import * as THREE from "three";

export type AvatarState = "idle" | "listening" | "thinking" | "speaking";

export interface Avatar {
  setState(s: AvatarState): void;
  setVolume(v: number): void;
  destroy(): void;
}

export function createAvatar(canvas: HTMLCanvasElement): Avatar {
  let destroyed = false;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 5;

  // Group to hold all head parts
  const headGroup = new THREE.Group();
  scene.add(headGroup);

  // ── Head ────────────────────────────────────────────────────────────────────
  const headGeo = new THREE.SphereGeometry(1, 64, 64);
  const headMat = new THREE.MeshStandardMaterial({
    color: 0x111111,
    metalness: 0.9,
    roughness: 0.1,
    envMapIntensity: 1,
  });
  const head = new THREE.Mesh(headGeo, headMat);
  headGroup.add(head);

  // ── Eyes ────────────────────────────────────────────────────────────────────
  const eyeGeo = new THREE.SphereGeometry(0.1, 32, 32);
  const eyeMat = new THREE.MeshBasicMaterial({ color: 0x4ca8e8 });
  
  const leftEye = new THREE.Mesh(eyeGeo, eyeMat);
  leftEye.position.set(-0.35, 0.3, 0.85);
  headGroup.add(leftEye);

  const rightEye = new THREE.Mesh(eyeGeo, eyeMat);
  rightEye.position.set(0.35, 0.3, 0.85);
  headGroup.add(rightEye);

  // ── Mouth ───────────────────────────────────────────────────────────────────
  const mouthGeo = new THREE.CapsuleGeometry(0.05, 0.4, 4, 16);
  mouthGeo.rotateZ(Math.PI / 2);
  const mouthMat = new THREE.MeshBasicMaterial({ color: 0x4ca8e8 });
  const mouth = new THREE.Mesh(mouthGeo, mouthMat);
  mouth.position.set(0, -0.4, 0.9);
  headGroup.add(mouth);

  // ── Lights ──────────────────────────────────────────────────────────────────
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
  scene.add(ambientLight);

  const pointLight = new THREE.PointLight(0x4ca8e8, 2, 10);
  pointLight.position.set(2, 2, 2);
  scene.add(pointLight);

  // ── State vars ──────────────────────────────────────────────────────────────
  let state: AvatarState = "idle";
  let volume = 0;
  const clock = new THREE.Clock();

  function animate() {
    if (destroyed) return;
    requestAnimationFrame(animate);

    const t = clock.getElapsedTime();

    // Floating motion
    headGroup.position.y = Math.sin(t * 0.5) * 0.1;
    headGroup.rotation.y = Math.sin(t * 0.2) * 0.1;

    // Lip sync
    if (state === "speaking") {
      const scaleV = 1 + volume * 5;
      mouth.scale.y = THREE.MathUtils.lerp(mouth.scale.y, scaleV, 0.3);
      mouth.material.color.setHSL(0.55, 0.8, 0.5 + volume * 0.5);
    } else {
      mouth.scale.y = THREE.MathUtils.lerp(mouth.scale.y, 0.1, 0.1);
      mouth.material.color.set(0x4ca8e8);
    }

    // Thinking pulse
    if (state === "thinking") {
      const p = (Math.sin(t * 10) + 1) / 2;
      eyeMat.color.setHSL(0.55, 0.8, 0.3 + p * 0.4);
    } else if (state === "listening") {
      eyeMat.color.set(0x00ff00);
    } else {
      eyeMat.color.set(0x4ca8e8);
    }

    renderer.render(scene, camera);
  }

  function onResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }

  window.addEventListener("resize", onResize);
  animate();

  return {
    setState(s: AvatarState) {
      state = s;
    },
    setVolume(v: number) {
      volume = v;
    },
    destroy() {
      destroyed = true;
      window.removeEventListener("resize", onResize);
      renderer.dispose();
    }
  };
}
