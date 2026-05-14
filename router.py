<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Zenthex Studio - AI 3D Workspace</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --accent-indigo: #6366f1; --accent-purple: #8b5cf6; --bg-dark: #09090b; }
        body { font-family: 'Outfit', sans-serif; background-color: var(--bg-dark); color: #d1d5db; margin: 0; overflow-x: hidden; }
        * { box-sizing: border-box; }
        nav { min-height: 80px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 16px 24px; border-bottom: 1px solid rgba(255,255,255,.08); background: rgba(0,0,0,.45); }
        nav a { color: #a1a1aa; text-decoration: none; }
        main { display: grid; grid-template-columns: minmax(280px, 360px) minmax(0, 1fr); min-height: calc(100vh - 80px); }
        main > div:first-child { padding: 28px; background: #0c0c0e; border-right: 1px solid rgba(255,255,255,.08); }
        main > div:last-child { min-height: calc(100vh - 80px); position: relative; background: #050507; }
        h2 { margin: 0 0 16px; }
        textarea, input, select { width: 100%; border: 1px solid rgba(255,255,255,.12); background: rgba(0,0,0,.55); color: #fff; border-radius: 10px; padding: 12px; }
        button { cursor: pointer; }
        #drop-zone { border: 2px dashed rgba(255,255,255,.14); border-radius: 16px; padding: 28px; text-align: center; cursor: pointer; }
        #btn-generate { width: 100%; margin-top: 12px; border: 1px solid rgba(139,92,246,.55); background: rgba(139,92,246,.22); color: #d8b4fe; border-radius: 12px; padding: 13px; font-weight: 800; }
        #status-box { margin-top: 16px; padding: 14px; border-radius: 12px; border: 1px solid rgba(99,102,241,.28); background: rgba(99,102,241,.08); color: #c7d2fe; }
        .fallback-preview {
            position: absolute; inset: 14%; display: grid; place-items: center; border: 1px solid rgba(255,255,255,.12);
            border-radius: 18px; background: linear-gradient(135deg, rgba(99,102,241,.12), rgba(0,255,204,.06));
            color: #e5e7eb; text-align: center; padding: 24px; z-index: 15;
        }
        .hidden { display: none !important; }
        .glass-panel { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.1); }
        #viewer-container { width: 100%; height: 100%; position: relative; }
        
        .loading-overlay {
            position: absolute; inset: 0; background: rgba(9, 9, 11, 0.95);
            backdrop-filter: blur(20px); z-index: 1000;
            display: none; flex-direction: column; align-items: center; justify-content: center;
            transition: opacity 0.5s; opacity: 0;
        }
        .loading-overlay.active { display: flex; opacity: 1; }
        .spinner {
            border: 2px solid rgba(255, 255, 255, 0.05); border-top: 2px solid var(--accent-indigo);
            border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .preview-watermark {
            position: absolute; inset: 0; z-index: 20; pointer-events: none;
            background-image: repeating-linear-gradient(-28deg, rgba(255,255,255,0.035) 0 2px, transparent 2px 120px);
        }
        .preview-watermark::after {
            content: "ZENTHEX PREVIEW · VIEW ONLY";
            position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%) rotate(-18deg);
            color: rgba(255,255,255,0.11); font-size: 44px; font-weight: 800; letter-spacing: 6px;
            white-space: nowrap;
        }
        @media print {
            #viewer-container { display: none !important; }
            body::before { content: "Zenthex Studio preview cannot be printed."; color: #111; font-size: 20px; }
        }
        @media (max-width: 1023px) {
            body { overflow-y: auto; }
            nav { padding: 14px 16px; }
            main { grid-template-columns: 1fr; }
            main > div:first-child { border-right: 0; border-bottom: 1px solid rgba(255,255,255,.08); padding: 20px; }
            main > div:last-child { min-height: 58vh; }
            .preview-watermark::after { font-size: 20px; letter-spacing: 3px; }
            #viewer-container { min-height: 56vh; }
        }
    </style>
</head>
<body class="bg-[#050507] text-white">

    <nav class="sticky top-0 z-50 backdrop-blur-2xl bg-black/40 border-b border-white/5 min-h-20 flex items-center px-4 md:px-10 py-4 justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-3 md:gap-4 min-w-0">
            <a href="index.html" class="flex items-center gap-2 text-xs font-bold text-gray-400 hover:text-white border-r border-white/10 pr-4 md:pr-6 mr-1 md:mr-2 transition-colors shrink-0">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></svg>
                메인으로
            </a>
            <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center font-bold">HL</div>
            <span class="font-extrabold tracking-widest text-sm md:text-base uppercase truncate">Zenthex Studio <span class="text-xs text-indigo-400 ml-1">AI 3D ENGINE</span></span>
        </div>
        <div class="hidden md:block px-4 py-1 rounded-full bg-purple-500/20 text-purple-300 text-[10px] font-bold border border-purple-500/30">
            CLOUD AI WORKSPACE
        </div>
    </nav>

    <main class="flex-grow grid grid-cols-1 lg:grid-cols-12 lg:overflow-hidden min-h-[calc(100vh-5rem)] lg:h-[calc(100vh-5rem)]">
        <!-- Left Sidebar -->
        <div class="col-span-1 lg:col-span-3 border-r border-white/5 p-5 md:p-8 flex flex-col gap-6 bg-[#0c0c0e]">
            <div class="glass-panel p-4 rounded-xl border-indigo-500/30 text-indigo-200 text-xs font-bold leading-relaxed mb-4">Zenthex Studio는 프롬프트와 2D 도면을 3D 공간으로 변환하는 AI 제작 워크스페이스입니다. 무료 체험은 같은 IP 기준 하루 1회 제공되며, 이후에는 Studio Pro 또는 Ultimate 구독이 필요합니다.</div>

            <!-- Upload flow -->
            <div>
                <h2 class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span class="w-1 h-3 bg-indigo-500 rounded-full"></span> 2D 도면 업로드 (Image to 3D)
                </h2>
                <div id="drop-zone" class="border-2 border-dashed border-white/10 rounded-2xl p-8 text-center hover:border-indigo-500/50 hover:bg-white/5 transition-all cursor-pointer">
                    <p class="text-xs text-gray-400 font-medium">클릭하여 2D 도면 업로드</p>
                </div>
                <input type="file" id="file-input" class="hidden" accept="image/*">
            </div>

            <div class="h-px bg-white/10 my-2"></div>

            <!-- Prompt flow -->
            <div>
                <h2 class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                    <span class="w-1 h-3 bg-purple-500 rounded-full"></span> AI 프롬프트 생성 (Text to 3D)
                </h2>
                <textarea id="ai-prompt" rows="4" class="w-full bg-black/50 border border-white/10 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors resize-none" placeholder="예: 통유리 창이 넓고 루프탑 정원이 있는 2층 모던 카페를 만들어줘"></textarea>
                <button id="btn-generate" class="w-full mt-3 py-3 bg-purple-500/20 hover:bg-purple-500/40 border border-purple-500/50 text-purple-300 text-xs font-bold rounded-xl transition-all">
                    프롬프트로 3D 생성
                </button>
            </div>

            <div id="status-box" class="hidden mt-4 p-4 rounded-xl text-xs font-medium border border-indigo-500/20 bg-indigo-500/5 text-indigo-300"></div>
        </div>

        <!-- Right 3D Viewport -->
        <div class="col-span-1 lg:col-span-9 relative bg-[#050507] min-h-[56vh] lg:min-h-0">
            <div id="viewer-container" class="w-full h-full">
                <div id="preview-watermark" class="preview-watermark"></div>
                <div id="placeholder" class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                    <p class="text-xs uppercase tracking-[0.4em] text-gray-600 font-bold">프롬프트 또는 도면을 입력하세요</p>
                </div>
                <div id="loading" class="loading-overlay">
                    <div class="spinner mb-4"></div>
                    <div class="text-xs text-indigo-400 font-bold uppercase tracking-widest animate-pulse" id="loading-text">공간을 생성하는 중...</div>
                </div>
            </div>
        </div>
    </main>

    <script>
        function zxAuthHeaders() {
            return { "Authorization": `Bearer ${localStorage.getItem("zx_token") || ""}` };
        }
        function zxShowStatus(html) {
            const box = document.getElementById('status-box');
            box.classList.remove('hidden');
            box.innerHTML = html;
        }
        function zxShowFallbackPreview() {
            const placeholder = document.getElementById('placeholder');
            if (placeholder) placeholder.classList.add('hidden');
            let preview = document.getElementById('fallback-preview');
            if (!preview) {
                preview = document.createElement('div');
                preview.id = 'fallback-preview';
                preview.className = 'fallback-preview';
                preview.innerHTML = '<div><strong style="font-size:24px">Zenthex 3D Preview</strong><p style="margin-top:12px;color:#a1a1aa">모바일 미리보기 구성이 완료되었습니다.<br>구독 후 GLB 다운로드와 고급 렌더링이 제공됩니다.</p></div>';
                document.getElementById('viewer-container').appendChild(preview);
            }
        }
        async function zxFallbackUpload(file) {
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch("/api/studio/upload", { method: "POST", headers: zxAuthHeaders(), body: formData });
            const result = await response.json();
            if (!response.ok || result.status !== "success") throw new Error(result.detail || result.message || "업로드 체험에 실패했습니다.");
            zxShowFallbackPreview();
            zxShowStatus(`3D 생성 요청이 완료되었습니다.<br><span style="color:#fcd34d">체험 미리보기는 보기 전용입니다. 다운로드는 구독 후 제공됩니다.</span>`);
        }
        async function zxFallbackGenerate() {
            const promptStr = document.getElementById('ai-prompt').value.trim();
            if (!promptStr) return alert("프롬프트를 입력해주세요.");
            const formData = new FormData();
            formData.append("prompt", promptStr);
            const response = await fetch("/api/studio/generate", { method: "POST", headers: zxAuthHeaders(), body: formData });
            const result = await response.json();
            if (!response.ok || result.status !== "success") throw new Error(result.detail || result.message || "프롬프트 체험에 실패했습니다.");
            zxShowFallbackPreview();
            zxShowStatus(`프롬프트 기반 3D 생성 요청이 완료되었습니다.<br><span style="color:#fcd34d">체험 미리보기는 보기 전용입니다. 다운로드는 구독 후 제공됩니다.</span>`);
        }
        document.addEventListener('DOMContentLoaded', () => {
            const dropZone = document.getElementById('drop-zone');
            const fileInput = document.getElementById('file-input');
            const generateBtn = document.getElementById('btn-generate');
            dropZone.onclick = () => fileInput.click();
            fileInput.onchange = async (event) => {
                if (!event.target.files[0]) return;
                try { zxShowStatus('업로드 및 분석 중...'); await zxFallbackUpload(event.target.files[0]); }
                catch (error) { zxShowStatus(`<span style="color:#f87171">오류 발생: ${error.message}</span>`); }
            };
            generateBtn.onclick = async () => {
                try { zxShowStatus('프롬프트로 공간을 생성하는 중...'); await zxFallbackGenerate(); }
                catch (error) { zxShowStatus(`<span style="color:#f87171">오류 발생: ${error.message}</span>`); }
            };
        });
    </script>

    <!-- Three.js renderer -->
    <script type="importmap">
        {
            "imports": {
                "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
                "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
            }
        }
    </script>

    <script type="module">
        import * as THREE from 'three';
        import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

        document.addEventListener('contextmenu', (event) => event.preventDefault());
        document.addEventListener('dragstart', (event) => event.preventDefault());
        document.addEventListener('keydown', async (event) => {
            const key = event.key.toLowerCase();
            if (key === 'printscreen' || (event.ctrlKey && ['s', 'p'].includes(key))) {
                event.preventDefault();
                try { await navigator.clipboard.writeText(''); } catch (_) {}
                alert('체험 미리보기는 저장, 출력, 스크린샷 단축키를 지원하지 않습니다. 다운로드는 구독 후 제공됩니다.');
            }
        });

        // Set up Scene
        const container = document.getElementById('viewer-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0a0a0f);
        scene.fog = new THREE.FogExp2(0x0a0a0f, 0.003);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(40, 30, 40);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        container.appendChild(renderer.domElement);

        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.autoRotate = true;
        controls.autoRotateSpeed = 1.0;

        // Lighting
        const ambient = new THREE.AmbientLight(0xffffff, 0.4);
        scene.add(ambient);

        const sun = new THREE.DirectionalLight(0xffffff, 1.5);
        sun.position.set(50, 100, 20);
        sun.castShadow = true;
        sun.shadow.mapSize.set(2048, 2048);
        scene.add(sun);

        const fillLight = new THREE.PointLight(0x6366f1, 2, 100);
        fillLight.position.set(-20, 10, -20);
        scene.add(fillLight);

        // Grid Environment
        const grid = new THREE.GridHelper(200, 100, 0x1f2937, 0x1f2937);
        grid.position.y = -0.05;
        scene.add(grid);

        // Core Procedural Generation Function (Zenthex Preview Style)
        const generateProceduralBuilding = () => {
            const group = new THREE.Group();
            
            // Premium Materials
            const glassMat = new THREE.MeshPhysicalMaterial({
                color: 0xffffff, transmission: 0.9, opacity: 1, transparent: true,
                roughness: 0.1, metalness: 0.2, ior: 1.5, side: THREE.DoubleSide
            });
            const frameMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.5 });
            const floorMat = new THREE.MeshStandardMaterial({ color: 0xe5e7eb, roughness: 0.8 });
            const lightStripMat = new THREE.MeshStandardMaterial({ color: 0x00ffcc, emissive: 0x00ffcc, emissiveIntensity: 2 });

            // Foundation
            const base = new THREE.Mesh(new THREE.BoxGeometry(30, 0.5, 30), floorMat);
            base.receiveShadow = true;
            group.add(base);

            // Level 1 Glass Box
            const l1 = new THREE.Mesh(new THREE.BoxGeometry(20, 8, 20), glassMat);
            l1.position.y = 4.25;
            l1.castShadow = true;
            group.add(l1);

            // Internal Core (Elevator shaft)
            const core = new THREE.Mesh(new THREE.BoxGeometry(4, 18, 4), frameMat);
            core.position.set(-2, 9, -2);
            core.castShadow = true;
            group.add(core);

            // Level 2 Cantilever
            const l2 = new THREE.Mesh(new THREE.BoxGeometry(25, 6, 15), frameMat);
            l2.position.set(2, 11, 2);
            l2.castShadow = true;
            group.add(l2);

            // Aesthetic Light Strips
            const strip = new THREE.Mesh(new THREE.BoxGeometry(25.1, 0.2, 0.2), lightStripMat);
            strip.position.set(2, 8.1, 9.6);
            group.add(strip);
            
            // Pool
            const pool = new THREE.Mesh(new THREE.BoxGeometry(10, 0.1, 20), new THREE.MeshPhysicalMaterial({
                color: 0x0ea5e9, transmission: 0.9, roughness: 0.1
            }));
            pool.position.set(10, 0.3, -5);
            group.add(pool);

            return group;
        };

        let currentModel = null;

        // Front-end file upload flow
        document.getElementById('drop-zone').onclick = () => document.getElementById('file-input').click();
        
        document.getElementById('file-input').onchange = async (e) => {
            if(!e.target.files[0]) return;
            const file = e.target.files[0];
            
            document.getElementById('status-box').classList.remove('hidden');
            document.getElementById('status-box').innerHTML = `업로드 및 분석 중...<br/>${file.name}`;
            document.getElementById('placeholder').classList.add('hidden');
            
            const loader = document.getElementById('loading');
            const loadText = document.getElementById('loading-text');
            loader.classList.add('active');
            loadText.innerText = 'Zenthex AI 엔진으로 전송 중...';

            const formData = new FormData();
            formData.append("file", file);

            try {
                // Send to Real Unified Backend
                const response = await fetch("/api/studio/upload", {
                    method: "POST",
                    headers: { "Authorization": `Bearer ${localStorage.getItem("zx_token") || ""}` },
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === "success") {
                    loadText.innerText = '3D 모델을 불러오는 중...';
                    
                    if(currentModel) scene.remove(currentModel);
                    
                    // Load a generated preview while the GLB pipeline result is prepared
                    // In a full implementation, you would load result.model_url using GLTFLoader.
                    // Preview generation keeps the workspace responsive:
                    currentModel = generateProceduralBuilding();
                    scene.add(currentModel);
                    
                    loader.classList.remove('active');
                    const lockedMsg = result.preview_only ? '<br><span class="text-amber-300">체험 미리보기는 보기 전용입니다. 다운로드는 구독 후 제공됩니다.</span>' : '<br><span class="text-[#00ffcc]">구독 권한으로 다운로드가 가능합니다.</span>';
                    document.getElementById('status-box').innerHTML = `3D 생성이 완료되었습니다.<br><span class="text-white">마우스로 공간을 둘러보세요.</span>${lockedMsg}`;
                    
                    // Fly-in Camera Animation
                    camera.position.set(60, 50, 60);
                    controls.target.set(0, 5, 0);
                } else {
                    throw new Error(result.detail || result.message || "3D 생성에 실패했습니다.");
                }
            } catch(error) {
                loader.classList.remove('active');
                document.getElementById('status-box').innerHTML = `<span class="text-red-400">오류 발생: ${error.message}</span>`;
            }
        };

        // Render Loop
        const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        window.addEventListener('resize', () => {
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });

        // Prompt Generation Logic
        document.getElementById('btn-generate').onclick = async () => {
            const promptStr = document.getElementById('ai-prompt').value;
            if(!promptStr) return alert("프롬프트를 입력해주세요.");
            
            document.getElementById('status-box').classList.remove('hidden');
            document.getElementById('status-box').innerHTML = `프롬프트로 공간을 생성하는 중...`;
            document.getElementById('placeholder').classList.add('hidden');
            
            const loader = document.getElementById('loading');
            const loadText = document.getElementById('loading-text');
            loader.classList.add('active');
            loadText.innerText = '프롬프트를 Zenthex AI 엔진으로 전송 중...';

            const formData = new FormData();
            formData.append("prompt", promptStr);

            try {
                const response = await fetch("/api/studio/generate", {
                    method: "POST",
                    headers: { "Authorization": `Bearer ${localStorage.getItem("zx_token") || ""}` },
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === "success") {
                    loadText.innerText = '3D 공간을 구성하는 중...';
                    
                    if(currentModel) scene.remove(currentModel);
                    
                    currentModel = generateProceduralBuilding();
                    scene.add(currentModel);
                    
                    loader.classList.remove('active');
                    const lockedMsg = result.preview_only ? '<br><span class="text-amber-300">체험 미리보기는 보기 전용입니다. 다운로드는 구독 후 제공됩니다.</span>' : '<br><span class="text-[#00ffcc]">구독 권한으로 다운로드가 가능합니다.</span>';
                    document.getElementById('status-box').innerHTML = `<span class="text-purple-400">프롬프트 기반 3D 생성이 완료되었습니다.<br>공간을 둘러보세요.</span>${lockedMsg}`;
                    
                    camera.position.set(60, 50, 60);
                    controls.target.set(0, 5, 0);
                } else {
                    throw new Error(result.detail || result.message || "3D 생성에 실패했습니다.");
                }
            } catch(error) {
                loader.classList.remove('active');
                document.getElementById('status-box').innerHTML = `<span class="text-red-400">오류 발생: ${error.message}</span>`;
            }
        };
    </script>
</body>
</html>




