"""Local single-browser history smoke checks. --live permits public FIMAP HTTPS.

Default mode mocks only the map engine, exercising the real page/animation JS.
Screenshots remain in the ignored historical generated directory.
"""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['APP_ENV'] = 'production'
os.environ['MAP_BASE_URL'] = 'https://iranmaptile.ir'
os.environ['MAP_ALLOWED_HOSTS'] = 'iranmaptile.ir'

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from app.routers.home import router
from app.core.demo_security import DemoSecurityMiddleware

MOCK = """
window.jQuery = {};
class MockMap {
 constructor(options) {this.options=options;this.sources={};this.layers={};window.historyTestMap=this;}
 on(name, callback) {if(name==='load') setTimeout(callback,10);}
 addControl() {}
 addSource(id, data) {this.sources[id]={data:data.data,setData(value){this.data=value;}};}
 getSource(id) {return this.sources[id];}
 addLayer(layer) {this.layers[layer.id]=layer;}
 setLayoutProperty(id,key,value) {this.layers[id][key]=value;}
 setFilter() {}
 fitBounds() {}
}
const pendingFrames = new Set(); window.maxHistoryFrames=0;
const originalRAF=window.requestAnimationFrame.bind(window), originalCancel=window.cancelAnimationFrame.bind(window);
window.requestAnimationFrame=cb=>{const id=originalRAF(t=>{pendingFrames.delete(id);cb(t);});pendingFrames.add(id);window.maxHistoryFrames=Math.max(window.maxHistoryFrames,pendingFrames.size);return id;};
window.cancelAnimationFrame=id=>{pendingFrames.delete(id);originalCancel(id);};
class MockMarker {
 constructor({element}) {this.element=element;}
 setLngLat(coordinate) {this.coordinate=coordinate;this.element.dataset.position=JSON.stringify(coordinate);return this;}
 addTo() {document.getElementById('history-map').appendChild(this.element);return this;}
 getElement() {return this.element;}
}
window.mapboxgl={Map:MockMap,Marker:MockMarker,config:{},NavigationControl:class {},
 LngLatBounds:class {extend(){return this;}},getRTLTextPluginStatus:()=> 'loaded'};
"""


def main():
    live = argparse.ArgumentParser()
    live.add_argument('--live', action='store_true')
    args = live.parse_args()
    app=FastAPI(); app.include_router(router)
    app.mount('/static',StaticFiles(directory=ROOT/'backend/app/static'),name='static')
    app.add_middleware(DemoSecurityMiddleware)
    client=TestClient(app)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1100})
        page=context.new_page()
        errors=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        mode={'failure':False}
        def serve(route):
            u=urlparse(route.request.url)
            if u.hostname=='preview.invalid':
                response=client.get(u.path)
                route.fulfill(status=response.status_code,body=response.content,
                              content_type=response.headers.get('content-type','text/plain'))
            elif u.hostname=='iranmaptile.ir' and mode['failure']:
                route.abort()
            elif args.live:
                route.continue_()
            elif u.path.endswith('.json'):
                route.fulfill(json={'version':8,'sources':{'openmaptiles':{}},'layers':[]})
            else:
                route.fulfill(body='',content_type='text/css' if u.path.endswith('.css') or 'google' in u.hostname else 'application/javascript')
        context.route('**/*',serve)
        if not args.live: page.add_init_script(MOCK)
        page.goto('https://preview.invalid/about',wait_until='domcontentloaded')
        page.wait_for_function("document.querySelectorAll('.history-truck').length===16",timeout=45000)
        if not args.live:
            assert page.evaluate("historyTestMap.sources['history-legacy'].data.features.length")==22
            assert page.evaluate('historyTestMap.options.maxZoom')==12
        page.locator('[data-stage="1"]').click()
        assert page.locator('#history-legacy').is_hidden()
        assert page.locator('#history-pending').is_visible()
        page.locator('[data-stage="2"]').click()
        page.wait_for_function("!document.getElementById('history-play').disabled",timeout=45000)
        assert page.locator('#history-legend button').count()==16
        assert page.locator('#history-play').get_attribute('aria-pressed')=='true'
        positions=page.locator('.history-truck').evaluate_all('(els)=>els.map(e=>e.dataset.position)')
        page.wait_for_timeout(600)
        page.locator('#history-play').click()
        if not args.live:
            moved=page.locator('.history-truck').evaluate_all('(els)=>els.map(e=>e.dataset.position)')
            assert all(a!=b for a,b in zip(positions,moved))
            assert page.evaluate("historyTestMap.sources['history-gps'].data.features.length")==16
            assert page.evaluate('maxHistoryFrames')==1
        value=page.locator('#history-timeline').input_value()
        assert int(value)>0
        page.wait_for_timeout(150)
        assert page.locator('#history-timeline').input_value()==value
        page.locator('#history-restart').click()
        assert page.locator('#history-timeline').input_value()=='0'
        for _ in range(3):
            page.locator('[data-stage="0"]').click()
            page.locator('[data-stage="2"]').click()
        page.locator('#history-play').click()  # Pause autoplay before the manual resume check.
        # Exercise background pause and foreground resumption without extra browsers.
        page.locator('#history-play').click()
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true}); document.dispatchEvent(new Event('visibilitychange'))")
        value=page.locator('#history-timeline').input_value()
        page.wait_for_timeout(150)
        assert page.locator('#history-timeline').input_value()==value
        page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:false}); document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_timeout(250)
        assert int(page.locator('#history-timeline').input_value())>int(value)
        page.emulate_media(reduced_motion='reduce')
        page.wait_for_timeout(100)
        assert page.locator('#history-play').get_attribute('aria-pressed')=='false'
        assert not errors,errors
        destination=ROOT/'data/history/kaleh/generated'
        if args.live:
            page.screenshot(path=str(destination/'about-desktop-live.png'),full_page=True)
        page.set_viewport_size({'width':360,'height':800})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if args.live: page.screenshot(path=str(destination/'about-mobile-live.png'),full_page=True)
        mode['failure']=True
        page.reload(wait_until='domcontentloaded')
        page.wait_for_function("document.getElementById('history-map-message').textContent.includes('نقشه در دسترس نیست')",timeout=18000)
        assert page.locator('h1').is_visible()
        assert page.locator('a[href="/demo/trial"]').last.is_visible()
        no_js=browser.new_context(java_script_enabled=False)
        no_js.route('**/*',serve)
        plain=no_js.new_page()
        plain.goto('https://preview.invalid/about',wait_until='domcontentloaded')
        assert plain.locator('[data-narrative="2"]').is_visible()
        assert plain.locator('noscript').is_visible()
        assert not errors,errors
        browser.close()
    print('PASS: '+('live FIMAP; ' if args.live else 'mocked map engine; ')+
          '16 routes, play/pause/restart, tab visibility, reduced motion, 360px, FIMAP failure, no JavaScript')


if __name__=='__main__': main()
