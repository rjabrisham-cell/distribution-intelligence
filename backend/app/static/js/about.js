/* Historical chapters consume only curated static datasets, never raw archives. */
(() => {
  'use strict';
  const root = document.querySelector('.history-page');
  const configElement = document.getElementById('history-config');
  if (!root || !configElement || root.dataset.started) return;
  root.dataset.started = 'true';
  const config = JSON.parse(configElement.textContent);
  const message = document.getElementById('history-map-message');
  const play = document.getElementById('history-play');
  const restart = document.getElementById('history-restart');
  const slider = document.getElementById('history-timeline');
  const time = document.getElementById('history-time');
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const format = new Intl.NumberFormat('fa-IR');
  let map, data, stage = 0, selected = null, frame = null, running = false;
  let progress = 0, previous = null, resumeOnVisible = false, ready = false;
  const showMessage = text => { message.hidden = false; message.textContent = text; };
  const empty = () => ({type: 'FeatureCollection', features: []});
  const layerErrors = [];

  function pause() {
    running = false;
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null; previous = null; play.textContent = 'پخش';
    play.setAttribute('aria-pressed', 'false');
  }
  const paths = new Map(), markers = new Map(), headings = new Map();
  let depotMarker = null;
  const depot=[51.554142,35.729941];
  let activeDay=null, sampleGPS=null, sampleAccess=null, sampleSmart=null, dayStart=0, dayEnd=86400, speed=1, dayRequest=0;
  let sampleDisplay=null,pendingDay=null;
  const calendarStatus=document.getElementById('history-calendar-status');
  document.getElementById('history-speed').addEventListener('change',event=>{speed=Number(event.target.value);});
  function preparePath(feature) {
    let total = 0;
    const edges = [];
    for (const segment of feature.geometry.coordinates) {
      for (let i = 1; i < segment.length; i++) {
        const a = segment[i-1], b = segment[i];
        const length = Math.hypot((b[0]-a[0])*Math.cos(a[1]*Math.PI/180), b[1]-a[1]);
        if (length) { edges.push({a,b,start:total,length}); total += length; }
      }
    }
    paths.set(feature.properties.route, {edges,total});
  }
  function bearing(a, b) {
    const p1 = a[1] * Math.PI / 180, p2 = b[1] * Math.PI / 180;
    const dl = (b[0] - a[0]) * Math.PI / 180;
    const y = Math.sin(dl) * Math.cos(p2);
    const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
  }
  function positionAt(feature, fraction) {
    const path = paths.get(feature.properties.route);
    if (!path.edges.length) return {coordinate:feature.geometry.coordinates[0][0], bearing:0};
    const distance = fraction*path.total;
    const edge = path.edges.find(e => e.start+e.length >= distance) || path.edges[path.edges.length-1];
    const t = Math.min(1,Math.max(0,(distance-edge.start)/edge.length));
    // Only interpolate recorded edges; never draw a line across missing segments.
    const index=path.edges.indexOf(edge);
    let x=0,y=0;
    for (let j=Math.max(0,index-2);j<=Math.min(path.edges.length-1,index+2);j++) {
      const e=path.edges[j]; if(e.length<.0003) continue;
      const angle=bearing(e.a,e.b)*Math.PI/180, weight=e.length/(1+Math.abs(index-j));
      x+=Math.cos(angle)*weight; y+=Math.sin(angle)*weight;
    }
    return {coordinate:edge.a.map((v,i) => v+(edge.b[i]-v)*t), bearing:Math.hypot(x,y)>1e-8?Math.atan2(y,x)*180/Math.PI:bearing(edge.a,edge.b)};
  }
  function draw(dt = 0) {
    slider.value = String(Math.round(progress * 1000));
    time.textContent = format.format(Math.round(progress * 100)) + '٪';
    if (!ready) return;
    const cars = empty();
    if(activeDay) time.textContent=clock(dayStart+progress*(dayEnd-dayStart));
    for (const feature of data.gps.features) {
      const pose = activeDay?calendarPose(feature,dayStart+progress*(dayEnd-dayStart)):positionAt(feature, progress), coordinate = pose.coordinate;
      const marker = markers.get(feature.properties.route);
      marker?.setLngLat(coordinate);
      if(marker) marker.getElement().hidden=stage!==2 || Boolean(pose.missing);
      const old=headings.get(feature.properties.route);
      const delta=old===undefined?0:((pose.bearing-old+540)%360+360)%360-180;
      const angle=old===undefined?pose.bearing:old+Math.max(-90*dt,Math.min(90*dt,delta));
      headings.set(feature.properties.route,angle);
      marker?.getElement().style.setProperty('--truck-bearing', `${angle}deg`);
      if (coordinate) cars.features.push({type:'Feature', properties:feature.properties,
        geometry:{type:'Point', coordinates:coordinate}});
    }
    map.getSource('history-cars').setData(cars);
  }
  function tick(timestamp) {
    frame = null;
    if (!running) return;
    if (previous !== null) progress = Math.min(1, progress + Math.min(timestamp - previous, 100)*speed / (activeDay?Math.max(1,dayEnd-dayStart)/300*1000:90000));
    const dt=previous===null?0:Math.min(timestamp-previous,100)/1000;
    previous = timestamp;
    draw(dt);
    if (progress >= 1) pause();
    else frame = requestAnimationFrame(tick);
  }
  function start() {
    if (!ready || running || stage !== 2 || document.hidden) return;
    if (progress >= 1) progress = 0;
    running = true; previous = null; play.textContent = 'توقف';
    play.setAttribute('aria-pressed', 'true');
    frame = requestAnimationFrame(tick);
  }
  function updateLayers() {
    if (!ready) return;
    for (const id of ['history-municipal','history-municipal-lines','history-regions','history-region-lines','history-region-labels']) map.setLayoutProperty(id,'visibility',stage===0?'visible':'none');
    for (const id of ['history-smart-regions','history-smart-lines','history-smart-labels']) map.setLayoutProperty(id,'visibility',stage===1?'visible':'none');
    map.setLayoutProperty('history-access','visibility',stage===2 || (stage===1 && activeDay)?'visible':'none');
    // Old outbound/return GPS is retained in its data file, not replayed as access.
    map.setLayoutProperty('history-transit','visibility','none');
    map.setLayoutProperty('history-traces','visibility',stage===2 || (stage===1 && activeDay)?'visible':'none');
    map.setPaintProperty('history-traces','line-opacity',selected===null?.8:['case',['==',['get','route'],selected],1,.2]);
    map.setPaintProperty('history-smart-regions','fill-opacity',selected===null?.55:['case',['==',['get','group'],selected],.8,.2]);
    root.querySelectorAll('.history-assignment-card').forEach(c=>c.setAttribute('aria-pressed',String(Number(c.dataset.group)===selected)));
    markers.forEach((marker,route) => { marker.getElement().hidden = stage!==2; marker.getElement().style.opacity=selected===null||selected===route?'1':'.3'; });
    if (depotMarker) depotMarker.getElement().hidden = stage !== 2;
    draw();
  }
  function fitStage() {
    if (!ready) return;
    map.resize();
    const collection = stage===0?data.municipal:stage===1?data.smart:data.gps;
    const bounds = new mapboxgl.LngLatBounds();
    function extend(coordinates) {
      if (typeof coordinates[0]==='number') bounds.extend(coordinates);
      else coordinates.forEach(extend);
    }
    collection.features.forEach(f=>extend(f.geometry.coordinates));
    if(stage===2) {extend(depot);data.access.features.forEach(f=>extend(f.geometry.coordinates));}
    if(collection.features.length) map.fitBounds(bounds,{padding:{top:55,bottom:145,left:35,right:35},maxZoom:11.5,duration:reduced.matches?0:300});
  }
  new ResizeObserver(()=>{if(map) map.resize();}).observe(document.getElementById('history-map'));
  new IntersectionObserver(entries=>{if(map && entries.some(e=>e.isIntersecting)) map.resize();}).observe(root);
  let resizeTimer;
  window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(fitStage,120);});
  function changeStage(next) {
    stage = next; pause(); resumeOnVisible = false;
    root.querySelectorAll('[data-stage]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.stage) === stage)));
    root.querySelectorAll('[data-narrative]').forEach(section => { section.hidden = Number(section.dataset.narrative) !== stage; });
    document.getElementById('history-legacy').hidden = stage !== 0;
    document.getElementById('history-smart-note').hidden = stage !== 1;
    document.getElementById('history-local-panel').hidden = stage === 0;
    document.querySelector('.history-narrative').classList.toggle('has-local-list',stage!==0);
    play.disabled = restart.disabled = slider.disabled = !ready || stage !== 2;
    updateLayers();
    fitStage();
    if (stage===2 && !reduced.matches) start();
  }
  root.querySelectorAll('[data-stage]').forEach(button => button.addEventListener('click', () => changeStage(Number(button.dataset.stage))));
  play.addEventListener('click', () => { resumeOnVisible = false; if (running) pause(); else start(); });
  restart.addEventListener('click', () => { pause(); resumeOnVisible = false; progress = 0; draw(); });
  slider.addEventListener('input', () => { pause(); resumeOnVisible = false; progress = Number(slider.value) / 1000; draw(); });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && map) map.resize();
    if (document.hidden) { resumeOnVisible = running; pause(); }
    else if (resumeOnVisible && !reduced.matches) { resumeOnVisible = false; start(); }
  });
  reduced.addEventListener('change', () => { if (reduced.matches) { pause(); resumeOnVisible = false; } });
  window.addEventListener('pagehide', pause);
  changeStage(0);

  const listDetails = document.getElementById('history-local-details');
  const mobileList = window.matchMedia('(max-width:700px)');
  const syncListLayout = () => { listDetails.open = !mobileList.matches; };
  mobileList.addEventListener('change', syncListLayout);
  syncListLayout();
  function rebuildMarkers() {
    markers.forEach(marker=>marker.remove());markers.clear();headings.clear();
        for (const feature of data.gps.features) {
          const element = document.createElement('div');
          element.className = 'history-truck';
          element.setAttribute('role','img');
          element.setAttribute('aria-label',String(feature.properties.route));
          element.innerHTML = '<span class="history-truck__heading"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 40" aria-hidden="true"><g fill="#172b40"><path d="M1 6h3v7H1zM20 6h3v7h-3zM1 28h3v8H1zM20 28h3v8h-3z"/></g><path d="M5 1h14l1 11H4z" fill="currentColor" stroke="#172b40"/><path d="M6 3h12v4H6z" fill="#b8dce9"/><path d="M4 14h16v24H4z" fill="currentColor" stroke="#172b40" stroke-width="1.5"/><path d="M6 16h12v19H6z" fill="none" stroke="#ffffff80"/><path d="M5 38h14" stroke="#172b40" stroke-width="2"/><path d="M5 37h3m8 0h3" stroke="#e77171" stroke-width="2"/></svg></span>';
          element.style.color = feature.properties.color;
          markers.set(feature.properties.route,new mapboxgl.Marker({element,anchor:'center'}).setLngLat(depot).addTo(map));
        }

  }
  function preparePlayback(gps,access) {
    paths.clear();
    for(const feature of gps.features) {
      const connections=access.features.filter(f=>f.properties.route===feature.properties.route);
      const arrival=connections.find(f=>f.properties.kind==='routed_access_not_recorded_gps');
      const segments=arrival?[arrival.geometry.coordinates]:[];
      const entry=connections.find(f=>f.properties.kind==='routed_full_gps_connection' && f.properties.after_segment===-1);
      if(entry)segments.push(entry.geometry.coordinates);
      feature.geometry.coordinates.forEach((segment,index)=>{
        segments.push(segment);
        const gap=connections.find(f=>f.properties.kind==='routed_full_gps_connection' && f.properties.after_segment===index);
        if(gap)segments.push(gap.geometry.coordinates);
      });
      preparePath({properties:feature.properties,geometry:{coordinates:segments}});
    }
  }
  function clock(second) {
    second=Math.max(0,Math.round(second));
    return [Math.floor(second/3600),Math.floor(second/60)%60,second%60].map(n=>String(n).padStart(2,'0')).join(':');
  }
  function calendarPose(feature,seconds) {
    const segments=feature.geometry.coordinates, times=feature.properties.times;
    const first=times[0][0];
    const access=data.access.features.find(f=>f.properties.route===feature.properties.route);
    if(seconds<first) {
      if(access && seconds>=first-access.properties.duration) {
        const path={properties:feature.properties};
        return positionAt(path,(seconds-first+access.properties.duration)/access.properties.duration);
      }
      return {coordinate:depot,bearing:0};
    }
    let last=segments[0][0];
    for(let s=0;s<segments.length;s++) {
      const ts=times[s], coords=segments[s];
      if(seconds<ts[0])return {coordinate:last,bearing:0,missing:true};
      for(let i=1;i<ts.length;i++)if(seconds<=ts[i]) {
        const t=(seconds-ts[i-1])/Math.max(1,ts[i]-ts[i-1]);
        const movement=Math.hypot((coords[i][0]-coords[i-1][0])*90500,(coords[i][1]-coords[i-1][1])*111000);
        return {coordinate:coords[i-1].map((v,j)=>v+(coords[i][j]-v)*t),bearing:movement<2?(headings.get(feature.properties.route)||0):bearing(coords[i-1],coords[i])};
      }
      last=coords[coords.length-1];
    }
    return {coordinate:last,bearing:headings.get(feature.properties.route)||0};
  }
  function setSmartRegions(regions) {
    data.smart=regions;
    map.getSource('history-smart').setData(regions);
    map.getSource('history-smart-centers').setData({type:'FeatureCollection',features:regions.features.map(f=>({
      type:'Feature',properties:f.properties,geometry:{type:'Point',coordinates:f.properties.label_center}
    }))});
  }
  async function loadDay(day) {
    const version=++dayRequest;pendingDay=day;pause();
    calendarStatus.textContent='در حال بارگذاری روز انتخاب‌شده…';
    try {
      const gps=await json(config.data_base+'calendar/'+day.file);
      let accessFailed=false;
      const access=await json(config.data_base+'calendar/'+day.date+'-access.geojson').catch(()=>{accessFailed=true;return empty();});
      let regionsFailed=false;
      const regionsURL=config.data_base+'calendar/'+day.date+'-regions.geojson';
      const regions=await json(regionsURL).catch(error=>{regionsFailed=true;console.error('[DIP calendar] '+regionsURL,error);return empty();});
      let classificationFailed=false;
      const classifiedURL=config.data_base+'calendar/'+day.date+'-operations.geojson';
      const classified=await json(classifiedURL).catch(error=>{classificationFailed=true;console.error('[DIP calendar] '+classifiedURL,error);return empty();});
      if(version!==dayRequest)return;
      if(!ready){calendarStatus.textContent='نقشه آماده نیست؛ اطلاعات روز بارگذاری شد.';applyDisplay(day.display,day.date);return;}
      activeDay=day.date;data.gps=gps;data.access=access;progress=0;selected=null;
      dayStart=Math.min(day.start,...gps.features.map(f=>f.properties.times[0][0]-(access.features.find(a=>a.properties.route===f.properties.route)?.properties.duration||0)));
      dayEnd=day.end;paths.clear();
      for(const f of gps.features) {
        const a=access.features.find(a=>a.properties.route===f.properties.route);
        preparePath({properties:f.properties,geometry:{coordinates:a?[a.geometry.coordinates]:[f.geometry.coordinates[0]]}});
      }
      // Rendering is classified; playback still consumes the complete unchanged
      // recording and the original depot access, preserving timestamps/movement.
      const renderedGPS=classificationFailed?gps:{type:'FeatureCollection',features:classified.features.filter(f=>f.properties.type==='operational_gps')};
      const renderedAccess=classificationFailed?access:{type:'FeatureCollection',features:classified.features.filter(f=>f.properties.type==='access_route')};
      map.getSource('history-gps').setData(renderedGPS);map.getSource('history-access').setData(renderedAccess);
      setSmartRegions(regions);
      pendingDay=null;rebuildMarkers();applyDisplay(day.display,day.date);changeStage(stage===1?1:2);
      calendarStatus.textContent=`${day.date} — ${format.format(gps.features.length)} خودرو؛ ساعت ثبت‌شده محلی`;
      if(accessFailed) calendarStatus.textContent+=' — مسیر دسترسی بارگذاری نشد؛ فقط ثبت GPS موجود نمایش داده می‌شود.';
      if(regionsFailed) document.getElementById('history-smart-note').textContent='محدوده‌های این روز بارگذاری نشد؛ مسیرها، آمار و کارت‌ها همچنان در دسترس‌اند.';
      if(classificationFailed) calendarStatus.textContent+=' — تفکیک مسیر بارگذاری نشد؛ ثبت کامل GPS نشان داده می‌شود.';
      document.querySelectorAll('[data-calendar-day]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.calendarDay===day.date)));
    } catch(error) {
      console.error('[DIP calendar] '+day.file,error);calendarStatus.textContent='بارگذاری این روز ممکن نشد؛ سایر روزها و نقشه در دسترس‌اند.';
    }
  }
  async function initializeCalendar() {
    try {
      const index=await json(config.data_base+'calendar/index.json');
      const days=document.getElementById('history-calendar-days');
      for(const day of index.days.filter(d=>index.selected_dates.includes(d.date))) {
        const button=document.createElement('button');button.type='button';button.dataset.calendarDay=day.date;
        button.textContent=`${day.date} — ${format.format(day.vehicles)} خودرو`;
        button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>loadDay(day));days.appendChild(button);
      }
    } catch(error) {console.error('[DIP calendar] index.json',error);calendarStatus.textContent='تقویم فعلاً در دسترس نیست؛ نقشه و کارت‌ها مستقل هستند.';}
  }
  document.getElementById('history-sample').addEventListener('click',()=>{
    ++dayRequest;pendingDay=null;pause();activeDay=null;progress=0;selected=null;
    if(sampleDisplay)applyDisplay(sampleDisplay,'sample');
    document.querySelectorAll('[data-calendar-day]').forEach(b=>b.setAttribute('aria-pressed','false'));
    if(!ready)return;
    data.gps=sampleGPS;data.access=sampleAccess;
    setSmartRegions(sampleSmart);
    preparePlayback(sampleGPS,sampleAccess);map.getSource('history-gps').setData(sampleGPS);map.getSource('history-access').setData(sampleAccess);
    rebuildMarkers();changeStage(stage===1?1:2);
  });

  function safeURL(value) {
    const url = new URL(value);
    if (!['https:','http:'].includes(url.protocol) || !config.map.allowed_hosts.includes(url.hostname)
        || url.username || url.password || (config.map.production && (url.protocol !== 'https:' || (url.port && url.port !== '443')))) {
      throw new Error('Map URL rejected');
    }
    return value;
  }
  function asset(url, css = false) {
    return new Promise((resolve, reject) => {
      const element = document.createElement(css ? 'link' : 'script');
      const timer = setTimeout(() => reject(new Error('Map asset timeout')), 12000);
      element.onload = () => { clearTimeout(timer); resolve(); };
      element.onerror = () => { clearTimeout(timer); reject(new Error('Map asset unavailable')); };
      if (css) { element.rel = 'stylesheet'; element.href = safeURL(url); }
      else element.src = safeURL(url);
      document.head.appendChild(element);
    });
  }
  async function json(url, external = false) {
    try {
    const response = await fetch(external ? safeURL(url) : url,
      {credentials:external ? 'omit':'same-origin', signal:AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
    } catch (error) {
      console.error(`[DIP history] Failed resource: ${url}`, error);
      throw error;
    }
  }
  function applyDisplay(summary,key) {
    const count=summary.groups.length;
    document.getElementById('history-orders').textContent=format.format(summary.orders);
    document.getElementById('history-assigned').textContent=format.format(summary.assigned_stores);
    document.getElementById('history-neighborhoods').textContent=format.format(count);
    document.getElementById('history-orders-note').textContent=summary.modeled?'سفارش‌های روز انتخاب‌شده':'فروشگاه‌های دارای سفارش در روز نمونه';
    document.getElementById('history-assigned-note').textContent=summary.modeled?'فروشگاه‌های دارای انتساب در روز انتخاب‌شده':'فروشگاه‌های تثبیت‌شده روز نمونه؛ ۱۰۲ مورد نیازمند بازبینی';
    document.getElementById('history-vehicles-note').textContent=`${format.format(count)} خودرو در روز انتخاب‌شده`;
    document.getElementById('history-sample').setAttribute('aria-pressed',String(key==='sample'));
    calendarStatus.textContent=`${key==='sample'?'روز نمونه':key} · ${format.format(count)} خودرو · ${format.format(count)} محله`;
    const grid=document.getElementById('history-assignment-grid');grid.replaceChildren();
    document.getElementById('history-day-overview').textContent=`${key==='sample'?'روز نمونه':key} · ${format.format(count)} کامیون · ${format.format(count)} محله · ${format.format(summary.assigned_stores)} فروشگاه با انتساب`;
    for(const group of summary.groups) {
      const card=document.createElement('button');card.type='button';card.className='history-assignment-card';card.dataset.group=group.group;card.setAttribute('aria-pressed','false');
      const dot=document.createElement('i');dot.className='history-local-color';dot.style.backgroundColor=group.color;dot.setAttribute('aria-hidden','true');
      const title=document.createElement('span');title.textContent=`محله ${format.format(group.group)}`;
      const truck=document.createElement('span');truck.textContent=`کامیون ${format.format(group.group)}`;
      const value=document.createElement('strong');value.textContent=`${format.format(group.store_count)} فروشگاه`;
      card.append(dot,title,truck,value);card.addEventListener('click',()=>{selected=selected===group.group?null:group.group;updateLayers();});grid.appendChild(card);
    }
    document.getElementById('history-smart-note').textContent=`${format.format(count)} محله هوشمند توزیع؛ ${format.format(summary.assigned_stores)} سوپرمارکت با انتساب`;
  }
  async function renderAssignments() {
    const url=config.data_base+(config.summary.datasets.smart_summary||'smart-summary.json');
    try {
      const summary=await json(url);
      sampleDisplay={orders:summary.daily_orders,assigned_stores:summary.assigned_stores,groups:summary.groups,modeled:false};
      if(!activeDay && !pendingDay)applyDisplay(sampleDisplay,'sample');
    } catch(error) {
      console.error('[DIP history] List unavailable: '+url,error);
      document.getElementById('history-assignment-grid').textContent='فهرست محله‌ها فعلاً در دسترس نیست.';
    }
  }
  async function initialize() {
    const layer = async name => {
      const url = config.data_base + name;
      try {
        const value = await json(url);
        if (value.type !== 'FeatureCollection' || !Array.isArray(value.features)) throw new Error('Invalid GeoJSON');
        return value;
      } catch (error) {
        console.error(`[DIP history] Layer unavailable: ${url}`, error);
        layerErrors.push(name);
        return empty();
      }
    };
    const [legacy, gps, smart, municipal, approvedAccess, transit, continuity] = await Promise.all([
      layer(config.summary.datasets.legacy),
      layer('operation-tracks.geojson'),
      layer(config.summary.datasets.smart || 'smart-regions.geojson'),
      layer('municipal-regions.geojson'),layer('access-routes.geojson'),layer('transit-tracks.geojson'),layer('gps-continuity.geojson')
    ]);
    const access={type:'FeatureCollection',features:[...approvedAccess.features.filter(f=>f.properties.kind==='routed_access_not_recorded_gps'),...continuity.features]};
    data = {legacy, gps, smart, municipal, access, transit};
    sampleGPS=gps;sampleAccess=access;sampleSmart=smart;
    preparePlayback(gps,access);
    if (!config.map.enabled) { showMessage('نمایش نقشه غیرفعال است؛ روایت و آمار همچنان در دسترس‌اند.'); return; }
    await asset(config.map.css, true);
    if (!window.jQuery && config.map.jquery) await asset(config.map.jquery);
    if (!window.mapboxgl) await asset(config.map.js);
    if (!window.mapboxgl) throw new Error('Compatible FIMAP engine unavailable');
    const style = await json(config.map.style, true);
    if (style.version !== 8 || !style.sources?.openmaptiles) throw new Error('Incompatible map style');
    style.glyphs = safeURL(config.map.glyph); style.sprite = safeURL(config.map.sprite);
    style.sources.openmaptiles = {type:'vector',tiles:[safeURL(config.map.tile)],minzoom:0,maxzoom:14};
    mapboxgl.config.API_URL = '';
    if (mapboxgl.getRTLTextPluginStatus() === 'unavailable') mapboxgl.setRTLTextPlugin(safeURL(config.map.rtl),null,true);
    map = new mapboxgl.Map({container:'history-map',style,center:[51.39,35.7],zoom:10,minZoom:8,maxZoom:12,hash:false,
      attributionControl:true,transformRequest:url => ({url:safeURL(url)})});
    map.addControl(new mapboxgl.NavigationControl({showCompass:false}), 'bottom-left');
    const timer = setTimeout(() => showMessage('نقشه هنوز آماده نشده است؛ متن روایت در دسترس است.'),15000);
    map.on('error', () => showMessage('بخشی از نقشه پایه بارگذاری نشد؛ روایت همچنان در دسترس است.'));
    map.on('load', () => {
      try {
        clearTimeout(timer);
        map.addSource('history-municipal',{type:'geojson',data:municipal});
        map.addSource('history-access',{type:'geojson',data:access});
        map.addSource('history-transit',{type:'geojson',data:transit});
        map.addSource('history-legacy',{type:'geojson',data:legacy});
        map.addSource('history-smart',{type:'geojson',data:smart});
        map.addSource('history-gps',{type:'geojson',data:gps});
        for (const [id,collection] of [['history-legacy-labels',legacy],['history-smart-centers',smart]]) {
          map.addSource(id,{type:'geojson',data:{type:'FeatureCollection',features:collection.features.map(f=>({type:'Feature',properties:f.properties,geometry:{type:'Point',coordinates:f.properties.label_center}}))}});
        }
        map.addSource('history-cars',{type:'geojson',data:empty()});
        map.addLayer({id:'history-municipal',type:'fill',source:'history-municipal',paint:{'fill-color':'#88949f','fill-opacity':.12}});
        map.addLayer({id:'history-municipal-lines',type:'line',source:'history-municipal',paint:{'line-color':'#647381','line-width':1.2,'line-opacity':.85}});
        map.addLayer({id:'history-access',type:'line',source:'history-access',layout:{visibility:'none'},paint:{'line-color':['get','color'],'line-width':1.6,'line-opacity':.65,'line-dasharray':[3,3]}});
        map.addLayer({id:'history-transit',type:'line',source:'history-transit',layout:{visibility:'none'},paint:{'line-color':['get','color'],'line-width':1,'line-opacity':.45}});
        map.addLayer({id:'history-regions',type:'fill',source:'history-legacy',paint:{'fill-color':['match',['%', ['get','region'],6],0,'#567c94',1,'#608d88',2,'#85839d',3,'#a18d70',4,'#7e956e','#9b7e87'],'fill-opacity':.6,'fill-opacity-transition':{duration:200}}});
        map.addLayer({id:'history-region-lines',type:'line',source:'history-legacy',paint:{'line-color':'#274e75','line-width':2}});
        map.addLayer({id:'history-region-labels',type:'symbol',source:'history-legacy-labels',layout:{'text-field':['to-string',['get','region']],'text-font':['VazirRegular'],'text-allow-overlap':true,'text-size':12},paint:{'text-color':'#14243e'}});
        map.addLayer({id:'history-smart-regions',type:'fill',source:'history-smart',layout:{visibility:'none'},paint:{'fill-color':['get','color'],'fill-opacity':.55}});
        map.addLayer({id:'history-smart-lines',type:'line',source:'history-smart',layout:{visibility:'none'},paint:{'line-color':'#174ea6','line-width':1.5,'line-opacity':.8}});
        map.addLayer({id:'history-smart-labels',type:'symbol',source:'history-smart-centers',layout:{visibility:'none','text-field':['concat','گروه ',['to-string',['get','group']]],'text-font':['VazirRegular'],'text-allow-overlap':true,'text-size':12},paint:{'text-color':'#0f2e55','text-halo-color':'#fff','text-halo-width':1}});
        map.addLayer({id:'history-traces',type:'line',source:'history-gps',paint:{'line-color':['get','color'],'line-width':2.5,'line-opacity':.65}});
        rebuildMarkers();
        const depotElement=document.createElement('div');depotElement.className='history-depot';
        depotElement.textContent='انبار مرکزی';
        depotMarker=new mapboxgl.Marker({element:depotElement,anchor:'bottom',offset:[0,-22]}).setLngLat(depot).addTo(map);
        const bounds = new mapboxgl.LngLatBounds();
        legacy.features.forEach(f => f.geometry.coordinates[0].forEach(p => bounds.extend(p)));
        if (legacy.features.length) map.fitBounds(bounds,{padding:35,duration:0,maxZoom:11});
        ready = true; message.hidden = true; changeStage(stage);
        if(pendingDay)loadDay(pendingDay);
        if(layerErrors.length) showMessage('برخی لایه‌ها بارگذاری نشدند؛ سایر بخش‌ها قابل استفاده‌اند: '+layerErrors.join('، '));
      } catch (_) { showMessage('نمایش مسیرها ممکن نشد؛ متن روایت همچنان قابل خواندن است.'); }
    });
  }
  renderAssignments();
  initializeCalendar();
  initialize().catch(error => { console.error('[DIP history] Map initialization failed', error); pause(); showMessage('نقشه در دسترس نیست؛ روایت تاریخی و اطلاعات صفحه همچنان قابل خواندن است.'); });
})();
