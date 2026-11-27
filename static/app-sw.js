// Cache only the public app shell. Account data, keys and API replies are never cached.
const CACHE='zenthex-mobile-v1';
const SHELL=['/app.html','/static/app.js','/static/app-icon-192.png','/static/app-icon-512.png'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL))));
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  for(const key of await caches.keys()) if(key.startsWith('zenthex-mobile-')&&key!==CACHE) await caches.delete(key);
  await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
  const url=new URL(event.request.url);
  if(event.request.method!=='GET'||url.origin!==self.location.origin||!SHELL.includes(url.pathname)) return;
  event.respondWith((async()=>{
    try {
      const response=await fetch(event.request,{cache:'no-store'});
      if(response.ok){const cache=await caches.open(CACHE);await cache.put(event.request,response.clone());}
      return response;
    } catch {
      return await caches.match(event.request)||new Response('연결을 확인해주세요.',{status:503});
    }
  })());
});
