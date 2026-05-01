/**
 * StockAI 3D Market Topology
 * Renders a Three.js powered constellation of global stocks.
 */

class MarketTopology {
    constructor() {
        this.canvasId = 'marketTopologyCanvas';
        this.stocks = [];
        this.nodes = [];
        this.connections = [];
        this.initialized = false;
        
        // Settings
        this.nodeCount = 25;
        this.connectionDensity = 0.15;
        
        if (document.getElementById(this.canvasId)) {
            this.initThree();
        }
    }

    async initThree() {
        // Load Three.js dynamically
        if (typeof THREE === 'undefined') {
            await this.loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');
        }

        const canvas = document.getElementById(this.canvasId);
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
        
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        
        // Build nodes
        this.createConstellation();
        
        this.camera.position.z = 30;
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
        const geometry = new THREE.SphereGeometry(0.2, 16, 16);
        const material = new THREE.MeshBasicMaterial({ color: 0xb8ff57 }); // Lime
        
        for (let i = 0; i < this.nodeCount; i++) {
            const node = new THREE.Mesh(geometry, material.clone());
            node.position.set(
                (Math.random() - 0.5) * 40,
                (Math.random() - 0.5) * 40,
                (Math.random() - 0.5) * 40
            );
            
            // Random velocities
            node.userData = {
                velocity: new THREE.Vector3(
                    (Math.random() - 0.5) * 0.02,
                    (Math.random() - 0.5) * 0.02,
                    (Math.random() - 0.5) * 0.02
                ),
                originalColor: 0xb8ff57
            };
            
            this.nodes.push(node);
            this.scene.add(node);
        }

        // Create random connections
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0x00f3ff, transparent: true, opacity: 0.1 });
        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                if (Math.random() < this.connectionDensity) {
                    const lineGeo = new THREE.BufferGeometry().setFromPoints([
                        this.nodes[i].position,
                        this.nodes[j].position
                    ]);
                    const line = new THREE.Line(lineGeo, lineMaterial);
                    this.connections.push({ line, start: this.nodes[i], end: this.nodes[j] });
                    this.scene.add(line);
                }
            }
        }
    }

    animate() {
        if (!this.initialized) return;
        requestAnimationFrame(() => this.animate());

        // Move nodes
        this.nodes.forEach(node => {
            node.position.add(node.userData.velocity);
            
            // Bounce
            if (Math.abs(node.position.x) > 20) node.userData.velocity.x *= -1;
            if (Math.abs(node.position.y) > 20) node.userData.velocity.y *= -1;
            if (Math.abs(node.position.z) > 20) node.userData.velocity.z *= -1;
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

        this.renderer.render(this.scene, this.camera);
    }
    
    // External hook to pulse the market
    pulse(sentimentScore) {
        const color = sentimentScore > 0 ? 0x00ffaa : (sentimentScore < 0 ? 0xff3e3e : 0xb8ff57);
        this.nodes.forEach(node => {
            node.material.color.setHex(color);
            // Flash effect
            setTimeout(() => {
                node.material.color.setHex(node.userData.originalColor);
            }, 1000);
        });
    }
}

// Global instance
window.marketTopology = new MarketTopology();
