/**
 * StockAI 3D Market Topology
 * Renders a Three.js powered constellation of global stocks.
 */

class MarketTopology {
    constructor() {
        this.canvasId = 'marketTopologyCanvas';
        this.nodes = [];
        this.connections = [];
        this.particles = [];
        this.initialized = false;
        
        // Settings
        this.nodeCount = 28;
        this.connectionDensity = 0.12;
        this.autoRotate = true;
        
        if (document.getElementById(this.canvasId)) {
            this.initThree();
        }
    }

    async initThree() {
        if (typeof THREE === 'undefined') {
            await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');
        }

        const canvas = document.getElementById(this.canvasId);
        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x0a0a0c, 0.015);

        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        
        // Create constellation
        this.createConstellation();
        
        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        const pointLight = new THREE.PointLight(0x00f3ff, 1, 100);
        pointLight.position.set(0, 10, 10);
        this.scene.add(pointLight);

        this.camera.position.z = 40;
        this.initialized = true;
        this.animate();

        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    loadScript(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = url;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createConstellation() {
        const geometry = new THREE.IcosahedronGeometry(0.3, 1);
        const symbols = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AMD', 'NFLX', 'BTC', 'ETH', 'GOLD', 'OIL'];

        for (let i = 0; i < this.nodeCount; i++) {
            const color = 0xb8ff57;
            const material = new THREE.MeshPhongMaterial({ 
                color: color, 
                emissive: color, 
                emissiveIntensity: 0.5,
                shininess: 100
            });
            
            const node = new THREE.Mesh(geometry, material);
            node.position.set(
                (Math.random() - 0.5) * 50,
                (Math.random() - 0.5) * 50,
                (Math.random() - 0.5) * 50
            );
            
            node.userData = {
                velocity: new THREE.Vector3((Math.random() - 0.5) * 0.03, (Math.random() - 0.5) * 0.03, (Math.random() - 0.5) * 0.03),
                originalColor: color,
                symbol: symbols[i % symbols.length]
            };
            
            this.nodes.push(node);
            this.scene.add(node);
            
            // Add label (simplified sprite for now)
            const sprite = this.makeTextSprite(node.userData.symbol);
            sprite.position.copy(node.position).add(new THREE.Vector3(0, 0.8, 0));
            node.userData.label = sprite;
            this.scene.add(sprite);
        }

        // Connections & Particles
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x00f3ff, transparent: true, opacity: 0.15 });
        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                if (Math.random() < this.connectionDensity) {
                    const lineGeo = new THREE.BufferGeometry().setFromPoints([this.nodes[i].position, this.nodes[j].position]);
                    const line = new THREE.Line(lineGeo, lineMaterial);
                    this.connections.push({ line, start: this.nodes[i], end: this.nodes[j] });
                    this.scene.add(line);
                    
                    // Add a flow particle
                    this.createParticle(this.nodes[i], this.nodes[j]);
                }
            }
        }
    }

    createParticle(startNode, endNode) {
        const pGeo = new THREE.SphereGeometry(0.08, 8, 8);
        const pMat = new THREE.MeshBasicMaterial({ color: 0x00f3ff, transparent: true, opacity: 0.8 });
        const particle = new THREE.Mesh(pGeo, pMat);
        particle.userData = {
            start: startNode,
            end: endNode,
            progress: Math.random(),
            speed: 0.002 + Math.random() * 0.005
        };
        this.particles.push(particle);
        this.scene.add(particle);
    }

    makeTextSprite(message) {
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        canvas.width = 128;
        canvas.height = 64;
        context.font = "Bold 32px 'JetBrains Mono', monospace";
        context.fillStyle = "rgba(255,255,255,0.8)";
        context.textAlign = "center";
        context.fillText(message, 64, 40);
        
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(4, 2, 1);
        return sprite;
    }

    animate() {
        if (!this.initialized) return;
        requestAnimationFrame(() => this.animate());

        const time = Date.now() * 0.001;

        // Auto Orbit
        if (this.autoRotate) {
            this.camera.position.x = 40 * Math.sin(time * 0.1);
            this.camera.position.z = 40 * Math.cos(time * 0.1);
            this.camera.lookAt(0, 0, 0);
        }

        // Move nodes
        this.nodes.forEach(node => {
            node.position.add(node.userData.velocity);
            
            // Boundary checks
            if (Math.abs(node.position.x) > 25) node.userData.velocity.x *= -1;
            if (Math.abs(node.position.y) > 25) node.userData.velocity.y *= -1;
            if (Math.abs(node.position.z) > 25) node.userData.velocity.z *= -1;
            
            // Update label position
            node.userData.label.position.copy(node.position).add(new THREE.Vector3(0, 1, 0));
        });

        // Update lines
        this.connections.forEach(conn => {
            const positions = conn.line.geometry.attributes.position.array;
            positions[0] = conn.start.position.x;
            positions[1] = conn.start.position.y;
            positions[2] = conn.start.position.z;
            positions[3] = conn.end.position.x;
            positions[4] = conn.end.position.y;
            positions[5] = conn.end.position.z;
            conn.line.geometry.attributes.position.needsUpdate = true;
        });

        // Update particles
        this.particles.forEach(p => {
            p.userData.progress += p.userData.speed;
            if (p.userData.progress > 1) p.userData.progress = 0;
            
            p.position.lerpVectors(p.userData.start.position, p.userData.end.position, p.userData.progress);
            
            // Pulse opacity
            p.material.opacity = 0.5 + Math.sin(time * 10 + p.userData.progress * 10) * 0.3;
        });

        this.renderer.render(this.scene, this.camera);
    }
    
    pulse(sentimentScore) {
        const color = sentimentScore > 0 ? 0x00ffaa : (sentimentScore < 0 ? 0xff3e3e : 0xb8ff57);
        const emIntensity = Math.abs(sentimentScore) * 2 + 0.5;

        this.nodes.forEach(node => {
            node.material.color.setHex(color);
            node.material.emissive.setHex(color);
            node.material.emissiveIntensity = emIntensity;
            
            setTimeout(() => {
                node.material.color.setHex(node.userData.originalColor);
                node.material.emissive.setHex(node.userData.originalColor);
                node.material.emissiveIntensity = 0.5;
            }, 1200);
        });
    }
}

// Global instance
window.marketTopology = new MarketTopology();
