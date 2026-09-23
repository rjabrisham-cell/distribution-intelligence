"""One real Chrome/FIMAP instance; local app via TestClient, no database writes."""
import os
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
os.environ.update(APP_ENV='production', MAP_BASE_URL='https://iranmaptile.ir', MAP_ALLOWED_HOSTS='iranmaptile.ir')
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from app.routers.home import router
from app.core.demo_security import DemoSecurityMiddleware
from playwright.sync_api import sync_playwright

app=FastAPI(); app.include_router(router)
app.mount('/static',StaticFiles(directory=ROOT/'backend/app/static'),name='static')
app.add_middleware(DemoSecurityMiddleware)
client=TestClient(app)
dest=ROOT/'tools/history/screenshots'; dest.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True,args=['--enable-webgl','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:print('CONSOLE',m.type,m.text[:350]) if m.type=='error' else None)
    def serve(route):
        u=urlparse(route.request.url)
        if u.hostname=='preview.invalid':
            r=client.get(u.path)
            route.fulfill(status=r.status_code,body=r.content,content_type=r.headers.get('content-type','text/plain'))
        else: route.continue_()
    page.route('**/*',serve)
    # Capture the real engine instance without replacing its implementation.
    page.add_init_script("""
    let engine;
    Object.defineProperty(window,'mapboxgl',{configurable:true,get(){return engine;},set(value){
      engine=value;const Original=value.Map;
      if(Original) value.Map=class extends Original {constructor(options){super(options);window.liveHistoryMap=this;}};
    }});
    """)
    assert page.goto('https://preview.invalid/about',wait_until='domcontentloaded').status==200
    page.wait_for_function("document.querySelectorAll('.history-truck').length===16",timeout=45000)
    page.wait_for_timeout(3000)
    print('MESSAGE',ascii(page.locator('#history-map-message').text_content()))
    print('TRUCKS',page.locator('.history-truck').count())
    assert page.locator('#history-assignment-grid .history-assignment-card').count()==16
    assert page.locator('.history-assignments, #history-legend').count()==0
    assert page.locator('#history-local-panel').is_hidden()
    assert 'تقویم و برنامه محله‌های توزیع' not in page.locator('body').inner_text()
    page.wait_for_function("document.querySelectorAll('#history-calendar-days button').length===5")
    assert page.locator('#history-calendar-days').count()==1
    assert page.evaluate("document.querySelector('#history-calendar-days').scrollWidth<=document.querySelector('#history-calendar-days').clientWidth")
    assert page.evaluate("document.querySelector('#history-calendar-days').getBoundingClientRect().bottom<=document.querySelector('.history-steps').getBoundingClientRect().top")
    page.locator('.history-story-head').screenshot(path=str(dest/'day-picker-desktop.png'))
    page.set_viewport_size({'width':360,'height':800});page.wait_for_timeout(700)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.evaluate("[...document.querySelectorAll('#history-calendar-days button')].every(b=>b.getBoundingClientRect().height>=44)")
    page.locator('.history-story-head').screenshot(path=str(dest/'day-picker-mobile.png'))
    page.locator('#history-calendar-days button').last.scroll_into_view_if_needed()
    page.locator('.history-story-head').screenshot(path=str(dest/'day-picker-mobile-end.png'))
    page.set_viewport_size({'width':1440,'height':1050});page.wait_for_timeout(700)
    assert sum(int(s.translate(str.maketrans(''.join(chr(1776+i) for i in range(10)),'0123456789')).split()[0]) for s in page.locator('.history-assignment-card strong').all_text_contents())==798
    for stage,name in [(0,'static'),(1,'smart'),(2,'movement')]:
        page.locator(f'[data-stage="{stage}"]').click()
        page.locator('.history-stage-layout').scroll_into_view_if_needed()
        page.wait_for_timeout(2500)
        if stage==2:
            page.locator('.history-stage-layout').screenshot(path=str(dest/'movement-start.png'))
            page.locator('#history-timeline').evaluate('(e)=>{e.value=300;e.dispatchEvent(new Event("input"));}')
            page.locator('#history-play').click();page.wait_for_timeout(1000)
        page.locator('.history-stage-layout').screenshot(path=str(dest/f'{name}.png'))
        if stage==0:
            assert page.evaluate("new Set(liveHistoryMap.queryRenderedFeatures({layers:['history-municipal']}).map(f=>f.properties.region)).size")==22
            assert page.locator('#history-local-panel').is_hidden()
        else:
            assert page.locator('#history-local-panel').is_visible()
            assert page.evaluate("document.querySelector('#history-assignment-grid').scrollHeight>document.querySelector('#history-assignment-grid').clientHeight")
            assert page.locator('#history-local-details').get_attribute('open') is not None
            page.locator('.history-stage-layout').screenshot(path=str(dest/f'sidebar-{name}-desktop.png'))
            if stage==1:
                page.locator('.history-assignment-card').nth(3).click()
                assert page.locator('.history-assignment-card').nth(3).get_attribute('aria-pressed')=='true'
                assert page.locator('[data-stage="1"]').get_attribute('aria-pressed')=='true'
                assert page.evaluate("liveHistoryMap.getPaintProperty('history-smart-regions','fill-opacity')[1][2]")==4
                page.locator('.history-assignment-card').nth(3).click()
        if stage<2:
            layer='history-regions' if stage==0 else 'history-smart-regions'
            key='region' if stage==0 else 'group'
            seen=page.evaluate('([id,key])=>[...new Set(liveHistoryMap.queryRenderedFeatures({layers:[id]}).map(f=>f.properties[key]))]',[layer,key])
            assert len(seen)==(22 if stage==0 else 16),(name,seen)
            print(name,'visible polygons',len(seen))
        assert page.evaluate("Math.abs(liveHistoryMap.getCanvas().clientHeight-document.querySelector('.history-map-wrap').clientHeight)<=1")
        assert page.evaluate("Math.abs(document.querySelector('.history-stage-layout').getBoundingClientRect().bottom-document.querySelector('.history-map-wrap').getBoundingClientRect().bottom)<=1")

    before=page.evaluate("[...document.querySelectorAll('.history-truck')].map(e=>e.style.transform)")
    page.wait_for_timeout(2500)
    after=page.evaluate("[...document.querySelectorAll('.history-truck')].map(e=>e.style.transform)")
    assert all(a!=b for a,b in zip(before,after)), (before,after)
    for value in ['200','450','750']:
        page.locator('#history-timeline').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input"));}',value)
        page.locator('#history-play').click()
        start=page.evaluate("performance.now()")
        angles=page.evaluate("[...document.querySelectorAll('.history-truck')].map(e=>parseFloat(e.style.getPropertyValue('--truck-bearing')))")
        page.wait_for_timeout(100)
        later=page.evaluate("[...document.querySelectorAll('.history-truck')].map(e=>parseFloat(e.style.getPropertyValue('--truck-bearing')))")
        elapsed=page.evaluate("performance.now()")-start
        assert all(abs(a-b)<=elapsed*.09+2 for a,b in zip(angles,later))
        page.locator('#history-play').click()
    page.locator('#history-restart').click()
    assert page.locator('#history-timeline').input_value()=='0'
    assert page.evaluate("liveHistoryMap.getSource('history-cars')._data.features.every(f=>Math.abs(f.geometry.coordinates[0]-51.554142)<1e-8 && Math.abs(f.geometry.coordinates[1]-35.729941)<1e-8)")
    page.locator('.history-assignment-card').nth(3).click()
    assert page.locator('.history-assignment-card').nth(3).get_attribute('aria-pressed')=='true'
    page.set_viewport_size({'width':360,'height':800});page.wait_for_timeout(1500)
    assert page.locator('#history-local-details').get_attribute('open') is None
    page.locator('.history-stage-layout').screenshot(path=str(dest/'sidebar-mobile-collapsed.png'))
    page.locator('#history-local-details summary').click()
    assert page.locator('#history-local-details').get_attribute('open') is not None
    assert page.locator('#history-assignment-grid').bounding_box()['height']<=225
    page.locator('.history-stage-layout').screenshot(path=str(dest/'sidebar-mobile-expanded.png'))
    page.locator('#history-local-details summary').click()
    page.locator('.history-map-wrap').screenshot(path=str(dest/'mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    for day,count in [('2010-04-21',15),('2010-04-22',15),('2010-04-24',14),('2010-04-25',11)]:
        page.locator(f'[data-calendar-day="{day}"]').click()
        page.wait_for_function('(day)=>document.querySelector(`[data-calendar-day="${day}"]`).getAttribute("aria-pressed")==="true"',arg=day)
        page.wait_for_function('(n)=>document.querySelectorAll("#history-assignment-grid .history-assignment-card").length===n',arg=count)
        expected=next(d['display'] for d in json.loads((ROOT/'backend/app/static/data/history/kaleh/calendar/index.json').read_text())['days'] if d['date']==day)
        normalize=lambda s:int(s.translate(str.maketrans(''.join(chr(1776+i) for i in range(10)),'0123456789')).replace(',','').replace('\u066c',''))
        assert normalize(page.locator('#history-orders').inner_text())==expected['orders']
        assert normalize(page.locator('#history-assigned').inner_text())==expected['assigned_stores']
        assert normalize(page.locator('#history-neighborhoods').inner_text())==count
        assert [normalize(s.split()[0]) for s in page.locator('.history-assignment-card strong').all_text_contents()]==[g['store_count'] for g in expected['groups']]
        assert page.locator('.history-truck').count()==count
        assert page.evaluate("""() => {
          const colors=new Map(liveHistoryMap.getSource('history-smart')._data.features.map(f=>[f.properties.group,f.properties.color]));
          const gps=new Map(liveHistoryMap.getSource('history-gps')._data.features.map(f=>[f.properties.route,f.properties.color]));
          return [...document.querySelectorAll('.history-assignment-card')].every(row=>{
            const route=Number(row.dataset.group), dot=row.querySelector('i');
            const probe=document.createElement('i');probe.style.backgroundColor=colors.get(route);
            const truck=document.querySelector(`.history-truck[aria-label="${route}"]`);
            return dot.style.backgroundColor===probe.style.backgroundColor && colors.get(route)===gps.get(route)
              && getComputedStyle(dot).backgroundColor===getComputedStyle(truck).color;
          });
        }""")
        assert page.evaluate("liveHistoryMap.getSource('history-gps')._data.features.length")==count
        assert page.evaluate("liveHistoryMap.getSource('history-gps')._data.features.every(f=>f.properties.type==='operational_gps')")
        assert page.evaluate("liveHistoryMap.getSource('history-access')._data.features.every(f=>f.properties.type==='access_route')")
        assert '\u0646\u0645\u0627\u06cc\u0634\u06cc' not in page.locator('body').inner_text()
        page.locator('.history-map-wrap').scroll_into_view_if_needed();page.wait_for_timeout(1200)
        page.locator('.history-map-wrap').screenshot(path=str(dest/f'calendar-{day}-mobile.png'))
        page.locator('#history-speed').select_option('4')
        page.set_viewport_size({'width':1440,'height':1050});page.wait_for_timeout(1000)
        page.locator('.history-stage-layout').screenshot(path=str(dest/f'calendar-{day}-desktop.png'))
        page.locator('[data-stage="1"]').click();page.wait_for_timeout(1000)
        assert page.locator('#history-local-panel').is_visible()
        assert page.evaluate("liveHistoryMap.getSource('history-smart')._data.features.length")==count
        assert page.evaluate("new Set(liveHistoryMap.queryRenderedFeatures({layers:['history-smart-regions']}).map(f=>f.properties.group)).size")==count
        page.locator('.history-stage-layout').screenshot(path=str(dest/f'smart-{day}.png'))
        for group in {'2010-04-21':[5,9],'2010-04-22':[11],'2010-04-25':[8]}.get(day,[]):
            page.locator(f'.history-assignment-card[data-group="{group}"]').click()
            page.evaluate("""group => {
              const f=liveHistoryMap.getSource('history-smart')._data.features.find(f=>f.properties.group===group);
              const xy=f.geometry.coordinates.flat(2).filter(Array.isArray);
              const points=f.geometry.type==='Polygon'?f.geometry.coordinates.flat():xy;
              liveHistoryMap.fitBounds([[Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1]))],
                [Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))]],{padding:45,duration:0,maxZoom:11});
            }""",group)
            page.wait_for_timeout(700)
            page.locator('.history-stage-layout').screenshot(path=str(dest/f'override-{day}-{group}.png'))
            page.locator(f'.history-assignment-card[data-group="{group}"]').click()
        page.set_viewport_size({'width':360,'height':800});page.wait_for_timeout(1000)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('#history-sample').click()
    page.wait_for_timeout(500)
    assert page.evaluate("liveHistoryMap.getSource('history-smart')._data.features.length")==16
    assert normalize(page.locator('#history-orders').inner_text())==970
    assert normalize(page.locator('#history-assigned').inner_text())==798
    for stage in range(3):
        page.locator(f'[data-stage="{stage}"]').click();page.wait_for_timeout(700)
        page.locator('.history-map-wrap').screenshot(path=str(dest/f'mobile-tab-{stage}.png'))
    assert not errors,errors
    print('PASS: real engine, polygons, 16 cards total 798, moving trucks, bounded heading, card selection, resize, mobile')
    print('SCREENSHOTS',dest)
    browser.close()
