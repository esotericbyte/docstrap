// build-tools.mjs — compile each tool's Svelte client source into the
// bundle its declaration names, and the viewer shell into its page.
//
// This script knows the *shape* of a tool build and nothing about any
// particular tool. It asks Python for the manifest
// (`docstrap.tools.frontend`), which reads the declarations, and then
// runs one small Vite library build per entry it is handed. No tool id
// and no bundle filename is written down here.
//
// Output goes back into the tool's own `static/` directory and is
// committed, so installing docstrap needs Python only. Node is a
// developer dependency of changing a tool's UI, not of using docstrap.
//
//   npm install     # once
//   npm run build   # after changing anything under a tool's ui/
import { execFileSync } from 'node:child_process';
import { readdirSync, statSync } from 'node:fs';
import { basename, dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

import { svelte, vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { build } from 'vite';

const packageRoot = dirname(fileURLToPath(import.meta.url));

/** The manifest, read off the declarations by the Python side. */
function readManifest() {
  const stdout = execFileSync(
    'uv',
    ['run', '--quiet', 'python', '-m', 'docstrap.tools.frontend'],
    { cwd: packageRoot, encoding: 'utf8' }
  );
  return JSON.parse(stdout);
}

function sizeOf(path) {
  try {
    return statSync(path).size;
  } catch {
    return 0;
  }
}

/**
 * One self-contained IIFE bundle per tool.
 *
 * IIFE because a tool is a plain <script> Sphinx adds to every page: no
 * module graph, no import map, nothing for the page to resolve. That
 * keeps the asset surface exactly what `register_tool_assets` already
 * registers, which is the surface the declaration owns.
 *
 * Self-contained is the cost of that: each bundle carries its own
 * tree-shaken copy of the Svelte runtime. Sharing one copy needs either
 * an untree-shaken runtime (measured: no saving at all) or ES-module
 * script tags so the bundles can share a chunk — and that would change
 * how a tool's bundle is served, so it is a decision to take
 * deliberately rather than a build detail. See README, "Tool UI build".
 *
 * CSS is emitted as a real file rather than injected from JS, because a
 * tool's stylesheet is a declared bundle (`declaration.css_bundle`) and
 * because the qa form's visibility is gated in CSS on markup the Sphinx
 * directive rendered — that rule has to apply before any script runs.
 * CSS is left unminified: it is small, it is read by humans reviewing
 * what a tool draws on a page, and it is the half of the output where
 * readability is worth more than the bytes.
 */
async function buildTool(target) {
  await build({
    configFile: false,
    root: packageRoot,
    logLevel: 'warn',
    // Library mode leaves `process.env.NODE_ENV` in place, and TanStack
    // Table guards its development checks with it; in a browser `process`
    // does not exist, so the first table built would throw. A tool bundle
    // is always a production build. No other tool reads it, so their
    // bundles come out the same.
    define: { 'process.env.NODE_ENV': JSON.stringify('production') },
    plugins: [
      svelte({
        preprocess: vitePreprocess(),
        compilerOptions: { discloseVersion: false },
      }),
    ],
    build: {
      outDir: target.outDir,
      // Modern enough to leave native private class fields alone.
      //
      // Vite's default target downlevels `#field` to a WeakMap, and
      // Svelte 5's error boundary reads a private field from a method
      // that can run before the downlevelled assignment has happened.
      // The symptom is a tool that mounts perfectly unminified and
      // throws `Cannot read properties of undefined (reading 'onerror')`
      // from inside Svelte's own runtime when built — an error which,
      // because it is thrown by the error handler, replaces whatever the
      // real error was and names nothing in the tool. Found by a
      // headless run on 2026-09-07.
      // The output is also smaller: WeakMap plumbing is not free.
      target: 'es2022',
      emptyOutDir: false,
      minify: 'esbuild',
      cssMinify: false,
      sourcemap: false,
      lib: {
        entry: target.entry,
        formats: ['iife'],
        name: `docstrapTool_${target.id.replace(/-/g, '_')}`,
        fileName: () => target.jsBundle,
        cssFileName: basename(target.cssBundle, '.css'),
      },
    },
  });
}

/**
 * The viewer shell: an application page, not a tool bundle.
 *
 * It differs from a tool's build in kind, and the
 * differences are deliberate. It is an ordinary module build of an HTML
 * page, because it is a page of its own and never a <script> Sphinx adds
 * to someone else's. And it is the ONLY build with Tailwind's plugin:
 * Skeleton is for instruments, not tools, and
 * the tool bundles above must come out byte-identical whether or not the
 * shell exists — their CSS is read by people reviewing what a tool draws.
 *
 * The output directory is the shell's own and nothing else's, so it is
 * emptied first; that is what keeps old hashed bundles from piling up.
 * Same build target as the tools, for the same reason (see above).
 */
async function buildShell(target) {
  await build({
    configFile: false,
    root: target.root,
    base: './',
    logLevel: 'warn',
    plugins: [
      // Must come before Svelte's, per Skeleton's installation guide.
      tailwindcss(),
      svelte({
        preprocess: vitePreprocess(),
        compilerOptions: { discloseVersion: false },
      }),
    ],
    build: {
      outDir: target.outDir,
      emptyOutDir: true,
      assetsDir: target.assetsDir,
      target: 'es2022',
      minify: 'esbuild',
      sourcemap: false,
      rollupOptions: { input: join(target.root, target.page) },
    },
  });
}

const { tools: manifest, shell } = readManifest();
if (manifest.length === 0) {
  console.warn('docstrap: no tool declares ui/index.ts — nothing to build');
}

for (const target of manifest) {
  await buildTool(target);
  for (const [index, file] of [target.jsBundle, target.cssBundle].entries()) {
    const path = join(target.outDir, file);
    console.log(
      `${(index === 0 ? target.id : '').padEnd(10)} ` +
        `${String(sizeOf(path)).padStart(7)} B  ${relative(packageRoot, path)}`
    );
  }
}

await buildShell(shell);
const shellFiles = [
  join(shell.outDir, shell.page),
  ...readdirSync(join(shell.outDir, shell.assetsDir))
    .sort()
    .map((file) => join(shell.outDir, shell.assetsDir, file)),
];
for (const [index, path] of shellFiles.entries()) {
  console.log(
    `${(index === 0 ? shell.id : '').padEnd(10)} ` +
      `${String(sizeOf(path)).padStart(7)} B  ${relative(packageRoot, path)}`
  );
}
