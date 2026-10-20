#!/usr/bin/env python3
"""Behavioral regressions for saved payload order and Quick Launch execution."""

from pathlib import Path
import shutil
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]


def run_node(body):
    node = shutil.which("node")
    if not node:
        raise AssertionError("Node.js is required for launch settings regressions")
    result = subprocess.run(
        [node, "-e", NODE_HARNESS + "\n" + body, str(REPO_ROOT)],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


NODE_HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[1];
const plain = value => JSON.parse(JSON.stringify(value));
function payload(id, extras = {}) {
    return Object.assign({
        id, displayTitle: id, description: '', author: '', toPort: 9021,
        supportedFirmwares: ['4.'], versions: [
            {version:'1.0', fileName:id+'.elf', filePath:'payloads/'+id+'/1.0/'+id+'.elf', isDefault:false},
            {version:'2.0', fileName:id+'.elf', filePath:'payloads/'+id+'/2.0/'+id+'.elf', isDefault:true},
        ],
    }, extras);
}
function boot(options = {}) {
    const stored = Object.assign({}, options.storage || {});
    const listeners = {}, dispatched = [], toasts = [];
    const timers = new Map();
    let timerId = 0, now = 0;
    class Element {
        constructor(tag) {
            this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {};
            this.style = {}; this.textContent = ''; this.disabled = false; this.hidden = false;
            this.events = {}; this.classes = new Set();
            this.classList = {
                add: (...names) => names.forEach(name => this.classes.add(name)),
                remove: (...names) => names.forEach(name => this.classes.delete(name)),
                contains: name => this.classes.has(name),
            };
        }
        get firstChild() { return this.children[0] || null; }
        get className() { return [...this.classes].join(' '); }
        set className(value) { this.classes = new Set(value.split(/\s+/).filter(Boolean)); }
        appendChild(child) { this.children.push(child); child.parentNode = this; return child; }
        removeChild(child) { this.children.splice(this.children.indexOf(child), 1); child.parentNode = null; }
        setAttribute(name, value) { this.attributes[name] = String(value); }
        getAttribute(name) { return this.attributes[name] || null; }
        addEventListener(name, fn) { (this.events[name] ||= []).push(fn); }
        click() { if (!this.disabled) for (const fn of this.events.click || []) fn.call(this, {target:this}); }
        querySelector(selector) {
            const all = this.querySelectorAll(selector); return all[0] || null;
        }
        querySelectorAll(selector) {
            const results = [];
            for (const child of this.children) {
                if (selector[0] === '.' ? child.classList.contains(selector.slice(1)) :
                    selector[0] === '#' ? child.attributes.id === selector.slice(1) :
                    child.tagName.toLowerCase() === selector.toLowerCase()) results.push(child);
                results.push(...child.querySelectorAll(selector));
            }
            return results;
        }
    }
    const grid = new Element('div');
    const document = {
        getElementById: id => id === 'payloads-view' ? grid : null,
        createElement: tag => new Element(tag),
        querySelector: selector => grid.querySelector(selector),
        querySelectorAll: selector => grid.querySelectorAll(selector),
    };
    const localStorage = {
        getItem(key) {
            if (options.readThrows) throw new Error('storage unavailable');
            return Object.hasOwn(stored, key) ? stored[key] : null;
        },
        setItem(key, value) {
            if (options.writeThrows) throw new Error('storage full');
            stored[key] = String(value);
        },
        removeItem(key) {
            if (options.writeThrows) throw new Error('storage full');
            delete stored[key];
        },
    };
    const context = {
        console: {error() {}, warn() {}, log() {}}, document, localStorage,
        payload_map: options.payloads || [payload('kstuff-lite'), payload('shadowmountplus'),
            payload('cheatrunner'), payload('orbit-store')],
        fw_str: '4.03',
        setTimeout(fn, delay, ...args) {
            const id = ++timerId;
            timers.set(id, {fn:() => fn(...args), at:now+Number(delay || 0)}); return id;
        },
        clearTimeout(id) { timers.delete(id); },
        addEventListener(name, fn) { (listeners[name] ||= []).push(fn); },
        removeEventListener(name, fn) {
            listeners[name] = (listeners[name] || []).filter(value => value !== fn);
        },
        dispatchEvent(event) {
            if (event.type === context.MAINLOOP_EXECUTE_PAYLOAD_REQUEST) dispatched.push(plain(event.detail));
            for (const fn of [...listeners[event.type] || []]) fn(event);
            return true;
        },
        CustomEvent: function(name, options) { this.type = name; this.detail = options?.detail; },
        showToast(message, timeout) {
            const toast = {message, timeout, removed:false}; toasts.push(toast); return toast;
        },
        updateToastMessage(toast, message) { if (toast) toast.message = message; },
        removeToast(toast) { if (toast) toast.removed = true; },
    };
    context.window = context;
    vm.createContext(context);
    for (const file of ['js/constants.js', 'js/settings-manager.js',
        'js/utils/firmware-compat.js', 'js/ui/payloads-view.js']) {
        vm.runInContext(fs.readFileSync(path.join(root, 'document/en/ps5', file), 'utf8'), context,
            {filename:file});
    }
    function advance(ms) {
        const target = now + ms;
        let runs = 0;
        while (true) {
            const due = [...timers].filter(([,item]) => item.at <= target)
                .sort((a,b) => a[1].at - b[1].at || a[0] - b[0])[0];
            if (!due) break;
            assert(++runs < 1000, 'Timer loop did not settle');
            now = due[1].at; timers.delete(due[0]); due[1].fn();
        }
        now = target;
    }
    return {
        api:context, stored, options, grid, dispatched, toasts, advance, timers,
        complete(request, success = true, error = '') {
            context.dispatchEvent(new context.CustomEvent(context.MAINLOOP_PAYLOAD_RESULT, {
                detail: {requestId:request.quickLaunchRequestId, success, error},
            }));
        },
    };
}
function configure(h, changes) {
    const settings = Object.assign(plain(h.api.getQuickLaunchSettings()), changes);
    assert.equal(h.api.setQuickLaunchSettings(settings), true);
}
"""


class SavedSettingsTests(unittest.TestCase):
    def test_defaults_and_saved_order_survive_new_payloads_and_reload(self):
        run_node(r"""
const h = boot();
assert.deepEqual(plain(h.api.getQuickLaunchSettings()), {
    enabled:true, payloadIds:['kstuff-lite','shadowmountplus','cheatrunner'],
    delayMs:3000, useSelectedVersions:false,
});
assert.equal(h.api.setPayloadOrder(['orbit-store','kstuff-lite','orbit-store','removed']), true);
assert.deepEqual(plain(h.api.getPayloadOrder()), ['orbit-store','kstuff-lite','shadowmountplus','cheatrunner']);
assert.deepEqual(plain(h.api.getOrderedPayloads()).map(p => p.id), plain(h.api.getPayloadOrder()));
const updated = boot({storage:h.stored, payloads:[...h.api.payload_map, payload('new-payload')]});
assert.deepEqual(plain(updated.api.getPayloadOrder()),
    ['orbit-store','kstuff-lite','shadowmountplus','cheatrunner','new-payload']);
assert.equal(updated.api.resetPayloadOrder(), true);
assert.deepEqual(plain(updated.api.getPayloadOrder()), updated.api.payload_map.map(p => p.id));
""")

    def test_configs_are_cloned_and_payload_choices_preserve_missing_ids(self):
        run_node(r"""
const h = boot();
configure(h, {payloadIds:['orbit-store','missing','orbit-store'], delayMs:1500, useSelectedVersions:true});
assert.deepEqual(plain(h.api.getQuickLaunchSettings().payloadIds), ['orbit-store','missing']);
const config = h.api.getQuickLaunchSettings(); config.payloadIds.push('shadowmountplus'); config.delayMs = 0;
assert.deepEqual(plain(h.api.getQuickLaunchSettings().payloadIds), ['orbit-store','missing']);
assert.equal(h.api.getQuickLaunchSettings().delayMs, 1500);
const reload = boot({storage:h.stored});
assert.deepEqual(plain(reload.api.getQuickLaunchSettings()), plain(h.api.getQuickLaunchSettings()));
assert.equal(reload.api.resetQuickLaunchSettings(), true);
assert.deepEqual(plain(reload.api.getQuickLaunchSettings().payloadIds),
    ['kstuff-lite','shadowmountplus','cheatrunner']);
""")

    def test_malformed_storage_is_isolated_from_valid_settings(self):
        run_node(r"""
const h = boot({storage:{payload_order:'{broken', quick_launch:'null',
    payload_visibility:'{"orbit-store":false}', payload_versions:'{"kstuff-lite":"1.0"}'}});
assert.equal(h.api.isPayloadVisible('orbit-store'), false);
assert.equal(h.api.getSelectedVersion('kstuff-lite'), '1.0');
assert.deepEqual(plain(h.api.getPayloadOrder()), h.api.payload_map.map(p => p.id));
assert.equal(h.api.getQuickLaunchSettings().delayMs, 3000);
const h2 = boot({storage:{payload_visibility:'null', payload_versions:'[]',
    quick_launch:JSON.stringify({enabled:false,payloadIds:[],delayMs:0,useSelectedVersions:true})}});
assert.equal(h2.api.getQuickLaunchSettings().enabled, false);
assert.equal(h2.api.isPayloadVisible('orbit-store'), true);
assert.equal(h2.api.getSelectedVersion('kstuff-lite'), null);
""")

    def test_invalid_values_and_storage_failures_preserve_active_settings(self):
        run_node(r"""
const h = boot();
const before = plain(h.api.getQuickLaunchSettings());
for (const changes of [{delayMs:-1},{delayMs:30001},{delayMs:Infinity},{delayMs:'3000'},
    {enabled:'yes'},{payloadIds:'kstuff-lite'},{payloadIds:[null]},{useSelectedVersions:1}]) {
    assert.equal(h.api.setQuickLaunchSettings(Object.assign({}, before, changes)), false);
    assert.deepEqual(plain(h.api.getQuickLaunchSettings()), before);
}
const order = plain(h.api.getPayloadOrder());
h.options.writeThrows = true;
assert.equal(h.api.setPayloadOrder(['orbit-store']), false);
assert.equal(h.api.setQuickLaunchSettings(Object.assign({}, before, {enabled:false})), false);
assert.equal(h.api.resetPayloadOrder(), false);
assert.equal(h.api.resetQuickLaunchSettings(), false);
assert.deepEqual(plain(h.api.getPayloadOrder()), order);
assert.deepEqual(plain(h.api.getQuickLaunchSettings()), before);
const blocked = boot({readThrows:true});
assert.deepEqual(plain(blocked.api.getQuickLaunchSettings()), before);
""")


class QuickLaunchTests(unittest.TestCase):
    def test_payload_grid_and_subtitle_follow_saved_order_and_choices(self):
        run_node(r"""
const h = boot();
h.api.setPayloadOrder(['orbit-store','cheatrunner','kstuff-lite','shadowmountplus']);
configure(h, {payloadIds:['orbit-store','kstuff-lite']});
h.api.populatePayloadsPage(false);
const cards = h.grid.children.filter(child => child.getAttribute('data-active-filepath'));
assert.deepEqual(cards.map(card => card.getAttribute('data-active-filepath').split('/')[1]),
    ['orbit-store','cheatrunner','kstuff-lite','shadowmountplus']);
assert.match(h.grid.querySelector('.quick-launch-subtitle').textContent, /orbit-store.*kstuff-lite/);
configure(h, {enabled:false}); h.api.populatePayloadsPage(false);
assert.equal(h.grid.querySelector('.quick-launch-btn'), null);
""")

    def test_whole_sequence_is_preflighted_before_dispatch(self):
        run_node(r"""
const invalids = [
    payload('bad',{supportedFirmwares:['5.']}),
    payload('bad',{customAction:'appcache-remove'}),
    payload('bad',{willHideEveryTime:true}),
    payload('bad',{versions:[]}),
];
for (const bad of invalids) {
    const h = boot({payloads:[payload('kstuff-lite'),bad]});
    configure(h,{payloadIds:['kstuff-lite','bad']});
    let result;
    assert.equal(h.api.startQuickLaunch(success => result = success), false);
    h.advance(60000);
    assert.equal(h.dispatched.length, 0);
    assert(!h.api.quickLaunchInProgress);
    assert.equal(result, false);
}
const missing = boot(); configure(missing,{payloadIds:['kstuff-lite','removed']});
assert.equal(missing.api.startQuickLaunch(), false); assert.equal(missing.dispatched.length, 0);
const empty = boot(); configure(empty,{payloadIds:[]});
assert.equal(empty.api.startQuickLaunch(), false); assert.equal(empty.dispatched.length, 0);
const disabled = boot(); configure(disabled,{enabled:false});
assert.equal(disabled.api.startQuickLaunch(), false); assert.equal(disabled.dispatched.length, 0);
const wk = boot({payloads:[payload('local',{toPort:0})]}); configure(wk,{payloadIds:['local']});
assert.equal(wk.api.startQuickLaunch(null,true), false); assert.equal(wk.dispatched.length, 0);
""")

    def test_hidden_choices_and_selected_or_default_versions_are_explicit(self):
        run_node(r"""
for (const selected of [false,true]) {
    const h = boot();
    h.api.setPayloadVisible('orbit-store', false);
    h.api.setSelectedVersion('orbit-store','1.0');
    configure(h,{payloadIds:['orbit-store'],useSelectedVersions:selected});
    assert.equal(h.api.startQuickLaunch(), true);
    assert.equal(h.dispatched.length,1);
    assert.equal(h.dispatched[0].version, selected ? '1.0' : '2.0');
    assert.equal(h.dispatched[0].filePath, 'payloads/orbit-store/'+(selected?'1.0':'2.0')+'/orbit-store.elf');
    h.complete(h.dispatched[0]);
    assert(!h.api.quickLaunchInProgress);
}
""")

    def test_waits_for_own_completion_then_configured_delay_and_final_result(self):
        run_node(r"""
const h = boot(); configure(h,{payloadIds:['orbit-store','kstuff-lite'],delayMs:1500});
let completed;
assert.equal(h.api.startQuickLaunch(success => completed = success), true);
assert.equal(h.dispatched.length,1);
assert(h.api.quickLaunchInProgress);
const first = h.dispatched[0]; assert(first.quickLaunchRequestId);
h.advance(60000); assert.equal(h.dispatched.length,1); assert.equal(completed,undefined);
h.complete({quickLaunchRequestId:'manual-unrelated'},false,'unrelated error');
assert(h.api.quickLaunchInProgress);
h.complete(first);
h.advance(1499); assert.equal(h.dispatched.length,1);
h.advance(1); assert.equal(h.dispatched.length,2);
const second = h.dispatched[1]; assert.notEqual(first.quickLaunchRequestId,second.quickLaunchRequestId);
h.complete(first,false,'stale duplicate'); assert(h.api.quickLaunchInProgress);
h.advance(60000); assert.equal(completed,undefined);
h.complete(second);
assert.equal(completed,true); assert(!h.api.quickLaunchInProgress);
assert.equal(h.api.quickLaunchToast,null);
""")

    def test_own_failure_aborts_and_reentry_cannot_create_duplicate_dispatches(self):
        run_node(r"""
const h = boot(); configure(h,{payloadIds:['orbit-store','kstuff-lite'],delayMs:0});
const completions = [];
assert.equal(h.api.startQuickLaunch(success => completions.push(success)),true);
assert.equal(h.api.startQuickLaunch(),false);
assert.equal(h.dispatched.length,1);
h.complete(h.dispatched[0],false,'send failed'); h.advance(60000);
assert.equal(h.dispatched.length,1); assert.deepEqual(completions,[false]);
assert(!h.api.quickLaunchInProgress); assert.equal(h.api.quickLaunchToast,null);
assert(h.toasts.some(toast => /send failed/.test(toast.message)));
assert.equal(h.api.startQuickLaunch(),true);
assert.equal(h.dispatched.length,2);
""")


    def test_main_queue_results_follow_actual_send_and_report_only_own_requests(self):
        run_node(r"""
(async () => {
    const h = boot();
    const source = fs.readFileSync(path.join(root,'document/en/ps5/main.js'),'utf8');
    const setupStart = source.indexOf('    let queue = [];');
    const setupEnd = source.indexOf('    // await log("Done, switching to payloads screen...", LogLevel.INFO);',setupStart);
    const workStart = source.indexOf('        if (queue.length > 0) {',setupEnd);
    const workEnd = source.indexOf('        if (queue.length > 0) {',workStart + 1);
    assert(setupStart >= 0 && setupEnd > setupStart && workStart > setupEnd && workEnd > workStart,
        'Could not isolate the real queue without evaluating the exploit');
    h.api.load_payload_into_elf_store_from_local_file = async () => 8;
    h.api.elf_store = {};
    h.api.wkOnly = true;
    let sendStarted = false, finishSend;
    h.api.send_buffer_to_port = async () => {
        sendStarted = true;
        await new Promise(resolve => {finishSend = resolve;});
    };
    vm.runInContext('(function () {' + source.slice(setupStart,setupEnd) +
        '\nwindow.processQueuedPayloads = async function () { while(queue.length > 0) {' +
        source.slice(workStart,workEnd) + '\n}};})();', h.api);
    const results = [];
    h.api.addEventListener(h.api.MAINLOOP_PAYLOAD_RESULT, event => results.push(plain(event.detail)));
    configure(h,{payloadIds:['orbit-store'],delayMs:0});
    assert(h.api.startQuickLaunch());
    const request = h.dispatched[0];
    const processing = h.api.processQueuedPayloads();
    await new Promise(resolve => setImmediate(resolve));
    assert(sendStarted,JSON.stringify(h.toasts)); assert.equal(results.length,0); assert(h.api.quickLaunchInProgress);
    assert.equal(h.toasts.length,1,'Quick Launch request must not create an individual toast');
    finishSend(); await processing;
    assert.deepEqual(results,[{requestId:request.quickLaunchRequestId,success:true}]);
    assert(!h.api.quickLaunchInProgress);
    const activeDuringSend = [];
    h.api.send_buffer_to_port = async () => {
        activeDuringSend.push(h.api.quickLaunchInProgress); throw new Error('send failed');
    };
    h.api.dispatchEvent(new h.api.CustomEvent(h.api.MAINLOOP_EXECUTE_PAYLOAD_REQUEST,{detail:payload('manual')}));
    assert(h.api.startQuickLaunch());
    await h.api.processQueuedPayloads();
    assert.deepEqual(activeDuringSend,[true,true], 'Manual failure must not abort the following Quick Launch request');
    assert.equal(results.length,2); assert.equal(results[1].success,false);
    assert.match(results[1].error,/send failed/); assert(!h.api.quickLaunchInProgress);
    const previousResults = results.length;
    h.api.dispatchEvent(new h.api.CustomEvent(h.api.MAINLOOP_EXECUTE_PAYLOAD_REQUEST,{detail:payload('manual')}));
    await h.api.processQueuedPayloads();
    assert.equal(results.length,previousResults,'Manual requests must not affect the launch completion channel');
    assert(h.toasts.some(toast => /manual/.test(toast.message)), 'Manual requests keep their own feedback');
})().catch(error => { console.error(error); process.exitCode = 1; });
""")


    def test_running_sequence_uses_snapshot_when_settings_change(self):
        run_node(r"""
const h = boot(); configure(h,{payloadIds:['orbit-store','kstuff-lite'],delayMs:500});
assert.equal(h.api.startQuickLaunch(),true);
configure(h,{payloadIds:['cheatrunner'],delayMs:0});
h.complete(h.dispatched[0]); h.advance(499); assert.equal(h.dispatched.length,1);
h.advance(1); assert.equal(h.dispatched[1].id,'kstuff-lite');
h.complete(h.dispatched[1]); assert(!h.api.quickLaunchInProgress);
""")


if __name__ == "__main__":
    unittest.main()
