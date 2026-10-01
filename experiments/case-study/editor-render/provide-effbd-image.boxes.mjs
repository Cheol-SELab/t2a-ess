/*******************************************************************************
 * Copyright: SELab.AI (c) 2026
 * provide-effbd-image.mjs
 *
  *   EFFBD rendering domain model -> PNG data URI (headless).
  *   Entry point for obtaining an image without opening a VS Code panel, used when the doc-editor
  *   embeds an .slb (EFFBD view) in an .sld document (called by the selab.effbd.renderToDataUri command).
  *
  *   The shared playwright plumbing (browser singleton, concurrency queue, context and cleanup) is delegated
  *   to withCapturePage of selab-image-capture; this file keeps only the EFFBD-specific SVG rendering flow.
  *   The Chromium binary is managed by selab-image-capture (see its README).
  *
  *   Study copy: additionally returns the node boxes of the rendered diagram (see below).
 *
 * API: renderEffbdModelToDataUri(payload, options?)
 *   payload = { model, metrics?, mode? ('EFFBD'|'FFBD'), offsetStates?, timeColumnStates? }
 *   options = { viewport?: {width,height}, configurationStates? }  (default 3840x2160)
 *******************************************************************************/

import { existsSync, readFileSync, readdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join, resolve } from 'path';
import {
    withCapturePage,
    toDataUri,
    injectThemeCss,
    waitForCaptureStability,
} from 'file:///G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-image-capture/src/index.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const LOG = '[provide-effbd-image]';

const EFFBD_EDITOR_ROOT = 'G:/SW/SW-SELab/selab-ex-system-modeler/packages/selab-effbd-editor';
const RENDER_DIR = join(EFFBD_EDITOR_ROOT, 'media', 'engine', 'render');
const STYLE_DIR = join(EFFBD_EDITOR_ROOT, 'media', 'style');
const ENGINE_DIR = join(EFFBD_EDITOR_ROOT, 'media', 'engine');
// Shared Modeler theme tokens (--modeler-*), loaded so that the export uses the same accent color as the
// webview; without them the fallback of css-variables.css applies. Their absence is not fatal (degrades to
// the fallback).
const MODELER_THEME_CSS = resolve(EFFBD_EDITOR_ROOT, '..', 'selab-ui', 'media', 'modeler-theme.generated.css');

// engine scripts required for rendering (peripheral/hub/overlay scripts such as selection and menus are not needed headless)
const REQUIRED_ENGINE_SCRIPTS = [
    'screen-fit.js',
];

const RENDER_SCRIPT_ORDER = [
    'node-bound.js',
    'node-text.js',
    'horizontal-layout.js',
    'bounding-box.js',
    'vertical-layout.js',
    'ffbd-layout.js',
    'enhanced-layout.js',
    'edge-connection.js',
    'edge-style.js',
    'edge-annotation.js',
    'edge-label.js',
    'performer-legend.js',
    'package-label.js',
    'edge-interaction.js',
    'region-subdivision.js',
    'data-injection.js',
    'diagram-renderer.js',
];

const STYLE_ORDER = [
    'css-variables.css',
    'base-layout.css',
    'loading-placeholder.css',
    'element-highlight.css',
    'edge-annotation.css',
    'edge-label.css',
    'performer-legend.css',
    'package-label.css',
    'model-sidebar.css',
    'context-menu.css',
    'modal-window.css',
    'inset-button.css',
    'cluster-indicator.css',
    'inline-modifier.css',
    'boundary-guideline.css',
    'touch-screen.css',
    'edge-style.css',
    'edge-interaction.css',
    'node-bound.css',
    'region-subdivision.css',
    'interaction-state.css',
    'enhanced-visibility.css',
    'origin-stamp.css',
    'screen-grid.css',
    'screen-watermark.css',
];

/** render script order, as in the live webview HtmlGenerator. */
function rendererScriptPaths() {
    if (!existsSync(RENDER_DIR)) throw new Error(`${LOG} media/engine/render missing: ${RENDER_DIR}`);
    const onDisk = readdirSync(RENDER_DIR).filter((f) => f.endsWith('.js'));
    const ordered = RENDER_SCRIPT_ORDER.filter((f) => onDisk.includes(f));
    const unlisted = onDisk.filter((f) => !RENDER_SCRIPT_ORDER.includes(f)).sort();
    return [...ordered, ...unlisted].map((f) => join(RENDER_DIR, f));
}

function loadCss() {
    if (!existsSync(STYLE_DIR)) return '';
    const themeCss = existsSync(MODELER_THEME_CSS) ? readFileSync(MODELER_THEME_CSS, 'utf-8') : '';
    return [themeCss, ...STYLE_ORDER
        .map((f) => {
            const cssPath = join(STYLE_DIR, f);
            if (!existsSync(cssPath)) {
                console.warn(`${LOG} missing css: ${cssPath}`);
                return '';
            }
            return readFileSync(cssPath, 'utf-8');
        })]
        .join('\n');
}

const HTML = (cssText) => `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
${cssText}
html,body{margin:0;padding:0;background:#fff}
#app{width:3840px;height:2160px;position:relative;overflow:hidden;color:#1e1e1e;
  --vscode-button-background:#bfbfbf;--vscode-editor-background:#ffffff;
  --vscode-editor-foreground:#1e1e1e;--vscode-foreground:#1e1e1e;
  --vscode-focusBorder:#007acc}
</style></head><body class="vscode-light"><div id="app"></div></body></html>`;

async function injectScripts(page) {
    for (const sp of rendererScriptPaths()) {
        if (!existsSync(sp)) { console.warn(`${LOG} missing: ${sp}`); continue; }
        await page.addScriptTag({ content: readFileSync(sp, 'utf-8') });
    }
    for (const name of REQUIRED_ENGINE_SCRIPTS) {
        const sp = join(ENGINE_DIR, name);
        if (existsSync(sp)) await page.addScriptTag({ content: readFileSync(sp, 'utf-8') });
    }
}

/**
 * Render an EFFBD rendering model and return a base64 data URI.
 *
 * @param {{model: object, metrics: object, mode?: 'EFFBD'|'FFBD', offsetStates?:object|null, timeColumnStates?:object|null}} payload
 * @param {{viewport?:{width:number,height:number}, configurationStates?:object}} [options]
 * @returns {Promise<string>} data:image/png;base64,...
 */
export async function renderEffbdModelToDataUri(payload, options = {}) {
    const {
        model,
        metrics,
        mode = 'EFFBD',
        offsetStates = null,
        timeColumnStates = null,
    } = payload || {};
    if (!model) throw new Error(`${LOG} model missing`);

    return withCapturePage(async (page) => {
        await page.setContent(HTML(loadCss()));
        await injectThemeCss(page, options.theme);
        await page.evaluate(() => {
            window.acquireVsCodeApi = () => ({ postMessage() {}, setState() {}, getState: () => ({}) });
            window.vscode = { postMessage() {} };
            window.EFFBD_TRANSLATIONS = { effbd: { messages: {}, buttons: {}, contextMenu: {} } };
        });
        await page.evaluate((configurationStates) => {
            for (const [key, value] of Object.entries(configurationStates || {})) {
                if (/^--[a-z0-9-]+$/i.test(key) && typeof value === 'string') {
                    document.documentElement.style.setProperty(key, value);
                }
            }
        }, options.configurationStates || {});

        await injectScripts(page);

        await page.evaluate(({ model, metrics, mode, offsetStates, timeColumnStates }) => {
            if (typeof window.renderEffbd !== 'function') throw new Error('window.renderEffbd is not defined');
            window.renderEffbd(document.getElementById('app'), model, {
                direction: 'LR',
                topologyMetrics: metrics || null,
                diagramMode: mode,
                offsetStates,
                timeColumnStates,
            });
        }, { model, metrics, mode, offsetStates, timeColumnStates });

        // Wait for the rendering to finish by a condition rather than a fixed sleep: `#app svg #vp` exists and its
        // getBBox() is non-zero, which the two following steps (FFBD hiding, bbox fitting) require anyway.
        // The upper bound stays at 800 ms, so the worst case equals a fixed 800 ms wait; if the condition is never met,
        // the code proceeds and the following steps guard themselves with `if (!vp) return`.
        await page.waitForFunction(() => {
            const svg = document.querySelector('#app svg');
            const vp = svg?.querySelector('#vp') || svg?._vp;
            if (!vp) return false;
            const bbox = vp.getBBox?.();
            return !!bbox && bbox.width > 0 && bbox.height > 0;
            // Poll at a fixed interval instead of rAF: the predicate forces layout through getBBox(), so calling it
            // every frame would cost CPU in a browser that is still rendering; 50 ms gives at most 16 polls in 800 ms.
        }, null, { timeout: 800, polling: 50 }).catch(() => {
            console.warn(`${LOG} render readiness condition not met (800 ms); proceeding`);
        });

        // in FFBD mode, hide ItemNode/ItemEdge
        if (mode === 'FFBD') {
            await page.evaluate(() => {
                const vp = document.querySelector('#app svg #vp') || document.querySelector('#app svg')?._vp;
                if (!vp) return;
                vp.querySelectorAll('g[data-initial-model*=\'"nodeElement":"ItemNode"\']').forEach((g) => g.style.display = 'none');
                vp.querySelectorAll('path[data-initial-model*="ItemInputEdge"], path[data-initial-model*="ItemOutputEdge"], path[data-initial-model*="TriggeringItemInputEdge"]').forEach((p) => p.style.display = 'none');
            });
        }

        // compute the actual diagram bounds and remove empty margins
        const PADDING = 16;
        await page.evaluate((pad) => {
            const svg = document.querySelector('#app svg');
            if (!svg) return;
            const vp = svg.querySelector('#vp') || svg._vp;
            if (!vp) return;
            const bbox = vp.getBBox();
            if (!bbox || bbox.width === 0 || bbox.height === 0) return;
            vp.setAttribute('transform', '');
            svg.setAttribute('viewBox', `${bbox.x - pad} ${bbox.y - pad} ${bbox.width + pad * 2} ${bbox.height + pad * 2}`);
            svg.setAttribute('width', String(bbox.width + pad * 2));
            svg.setAttribute('height', String(bbox.height + pad * 2));
            const app = document.getElementById('app');
            app.style.width = (bbox.width + pad * 2) + 'px';
            app.style.height = (bbox.height + pad * 2) + 'px';
        }, PADDING);
        // Keep this 300 ms wait: it is probably redundant with waitForCaptureStability (fonts.ready + 2 rAF) below,
        // but it is not removed without a measurement, because a wrong removal would capture during layout.
        await page.waitForTimeout(300);
        await waitForCaptureStability(page);

        const boxes = await page.evaluate(() => {
            const app = document.getElementById('app').getBoundingClientRect();
            const nodes = [...document.querySelectorAll('#app svg g[data-id][data-initial-model]')].map((g) => {
                let m = {};
                try { m = JSON.parse(g.getAttribute('data-initial-model')); } catch { /* ignore */ }
                const r = g.getBoundingClientRect();
                return { kind: 'node', id: g.getAttribute('data-id'), nodeElement: m.nodeElement, parent: m.parentFunctionNodeIdentifier ?? null,
                         x: r.left - app.left, y: r.top - app.top, width: r.width, height: r.height };
            });
            const regions = [...document.querySelectorAll('#app svg g[data-parent-id][data-region-type="subdivision"]')].map((g) => {
                const r = g.getBoundingClientRect();
                return { kind: 'region', id: g.getAttribute('data-parent-id'), x: r.left - app.left, y: r.top - app.top, width: r.width, height: r.height };
            });
            return [...nodes, ...regions];
        });
        const buf = await page.locator('#app').screenshot();
        return { dataUri: toDataUri(buf), boxes };
    }, {
        viewport: options.viewport || { width: 3840, height: 2160 },
        deviceScaleFactor: 2,
    });
}
