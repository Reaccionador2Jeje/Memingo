import * as THREE from "three";

const canvas = document.querySelector("#game-canvas");
const startScreen = document.querySelector("#start-screen");
const startButton = document.querySelector("#start-button");
const pauseScreen = document.querySelector("#pause");
const resumeButton = document.querySelector("#resume-button");
const positionLabel = document.querySelector("#position");
const blocksLabel = document.querySelector("#blocks-count");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x79c6ed);
scene.fog = new THREE.Fog(0x79c6ed, 18, 58);
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 150);
camera.position.set(0, 8, 12);

const world = new THREE.Group();
scene.add(world);

const sun = new THREE.DirectionalLight(0xfff4c8, 1.8);
sun.position.set(-18, 32, 12);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -30;
sun.shadow.camera.right = 30;
sun.shadow.camera.top = 30;
sun.shadow.camera.bottom = -30;
scene.add(sun);
scene.add(new THREE.HemisphereLight(0xc8eaff, 0x4a6b36, 1.35));

const materials = {
  grass: { color: 0x62a84d, top: 0x78bd56 },
  stone: { color: 0x858b87 },
  wood: { color: 0x8d5b35 },
  sand: { color: 0xd9c98a },
  glass: { color: 0xa9dde7, transparent: true, opacity: 0.62 }
};

const blockGeometry = new THREE.BoxGeometry(1, 1, 1);
const materialCache = {};
const blocks = new Map();
let selectedBlock = "grass";
let placedBlocks = 0;

function hash(x, z) {
  const value = Math.sin(x * 127.1 + z * 311.7 + 404) * 43758.5453123;
  return value - Math.floor(value);
}

function terrainHeight(x, z) {
  const broad = Math.sin(x * 0.22) * 1.3 + Math.cos(z * 0.18) * 1.2;
  const detail = (hash(x, z) - 0.5) * 1.5;
  return Math.max(1, Math.floor(4 + broad + detail));
}

function blockKey(x, y, z) { return `${x},${y},${z}`; }

function getMaterial(type, face) {
  const key = `${type}-${face || "side"}`;
  if (materialCache[key]) return materialCache[key];
  const data = materials[type];
  const color = face === "top" && data.top ? data.top : data.color;
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: type === "glass" ? 0.15 : 0.82,
    metalness: 0,
    transparent: data.transparent || false,
    opacity: data.opacity || 1
  });
  materialCache[key] = material;
  return material;
}

function addBlock(x, y, z, type = "grass", userPlaced = false) {
  const key = blockKey(x, y, z);
  if (blocks.has(key)) return null;
  let mesh;
  if (type === "grass") {
    mesh = new THREE.Mesh(blockGeometry, [
      getMaterial("grass"), getMaterial("grass"), getMaterial("grass", "top"),
      getMaterial("grass"), getMaterial("grass"), getMaterial("grass")
    ]);
  } else {
    mesh = new THREE.Mesh(blockGeometry, getMaterial(type));
  }
  mesh.position.set(x, y, z);
  mesh.castShadow = type !== "glass";
  mesh.receiveShadow = true;
  mesh.userData = { type, x, y, z, userPlaced };
  world.add(mesh);
  blocks.set(key, mesh);
  if (userPlaced) {
    placedBlocks += 1;
    blocksLabel.textContent = String(placedBlocks);
  }
  return mesh;
}

function removeBlock(mesh) {
  if (!mesh || !mesh.userData) {
    return false;
  }
  const { x, y, z } = mesh.userData;
  world.remove(mesh);
  blocks.delete(blockKey(x, y, z));
  placedBlocks = Math.max(0, placedBlocks - 1);
  blocksLabel.textContent = String(placedBlocks);
  return true;
}

function generateWorld() {
  const size = 18;
  for (let x = -size; x <= size; x++) {
    for (let z = -size; z <= size; z++) {
      const height = terrainHeight(x, z);
      for (let y = 0; y <= height; y++) {
        let type = "stone";
        if (y === height) type = height <= 4 ? "sand" : "grass";
        else if (y >= height - 2) type = "dirt";
        addBlock(x, y, z, materials[type] ? type : "stone");
      }
      if (hash(x, z) > 0.975 && height > 5 && Math.abs(x) > 4 && Math.abs(z) > 4) {
        for (let y = 1; y <= 3; y++) addBlock(x, height + y, z, "wood");
        for (let lx = -1; lx <= 1; lx++) for (let lz = -1; lz <= 1; lz++) {
          for (let ly = 3; ly <= 4; ly++) if (lx || lz || ly === 3) addBlock(x + lx, height + ly, z + lz, "grass");
        }
      }
    }
  }

  addBlock(0, 6, 0, "glass", true);
}

generateWorld();

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(120, 120),
  new THREE.MeshStandardMaterial({ color: 0x4da5d4, transparent: true, opacity: 0.72, roughness: 0.1 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = 0.05;
ground.receiveShadow = true;
scene.add(ground);

const clouds = new THREE.Group();
const cloudMaterial = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.88 });
for (let index = 0; index < 14; index++) {
  const cloud = new THREE.Mesh(new THREE.BoxGeometry(4 + hash(index, 2) * 4, 0.8, 1.4 + hash(index, 8) * 1.5), cloudMaterial);
  cloud.position.set((hash(index, 1) - 0.5) * 70, 20 + hash(index, 3) * 8, (hash(index, 4) - 0.5) * 70);
  clouds.add(cloud);
}
scene.add(clouds);

const keys = new Set();
let yaw = 0;
let pitch = -0.18;
let velocityY = 0;
let grounded = false;
let started = false;
let paused = false;
let mobileForward = 0;
let mobileTurn = 0;

const player = new THREE.Object3D();
player.position.set(0, 8, 8);
scene.add(player);
player.add(camera);
camera.position.set(0, 0.55, 0);

function getBlockAt(x, y, z) { return blocks.get(blockKey(Math.round(x), Math.round(y), Math.round(z))); }

function canStandAt(x, y, z) {
  const radius = 0.32;
  for (const ox of [-radius, radius]) for (const oz of [-radius, radius]) {
    const block = getBlockAt(x + ox, y - 1.05, z + oz);
    if (block) return true;
  }
  return false;
}

function updatePlayer(delta) {
  yaw -= (keys.has("mouseX") ? 0 : 0);
  player.rotation.y = yaw;
  camera.rotation.x = pitch;

  const move = new THREE.Vector3();
  const forward = keys.has("KeyW") || mobileForward > 0.2;
  const backward = keys.has("KeyS") || mobileForward < -0.2;
  const left = keys.has("KeyA") || mobileTurn < -0.2;
  const right = keys.has("KeyD") || mobileTurn > 0.2;
  if (forward) move.z -= 1;
  if (backward) move.z += 1;
  if (left) move.x -= 1;
  if (right) move.x += 1;
  if (move.lengthSq()) {
    move.normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), yaw).multiplyScalar(7 * delta);
    const nextX = player.position.x + move.x;
    const nextZ = player.position.z + move.z;
    if (!getBlockAt(nextX, player.position.y - 1, nextZ) && !getBlockAt(nextX, player.position.y, nextZ)) player.position.x = nextX;
    if (!getBlockAt(player.position.x, player.position.y - 1, nextZ) && !getBlockAt(player.position.x, player.position.y, nextZ)) player.position.z = nextZ;
  }

  velocityY -= 22 * delta;
  player.position.y += velocityY * delta;
  if (canStandAt(player.position.x, player.position.y, player.position.z)) {
    const groundY = terrainHeight(Math.round(player.position.x), Math.round(player.position.z));
    if (velocityY <= 0) {
      player.position.y = Math.max(player.position.y, groundY + 1.05);
      velocityY = 0;
      grounded = true;
    }
  } else {
    grounded = false;
  }

  if (player.position.y < -4) player.position.set(0, 9, 8);
}

const raycaster = new THREE.Raycaster();
raycaster.far = 6;
const pointer = new THREE.Vector2(0, 0);

function raycastPlace(button = 0) {
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects([...blocks.values()])[0];
  if (!hit) return;
  if (button === 2 || keys.has("KeyR")) return removeBlock(hit.object);
  const normal = hit.face?.normal?.clone().applyQuaternion(hit.object.quaternion);
  if (!normal) return;
  const x = Math.round(hit.object.position.x + normal.x);
  const y = Math.round(hit.object.position.y + normal.y);
  const z = Math.round(hit.object.position.z + normal.z);
  addBlock(x, y, z, selectedBlock, true);
}

canvas.addEventListener("click", () => {
  if (!started || paused) return;
  if (document.pointerLockElement !== canvas) canvas.requestPointerLock?.();
});
document.addEventListener("pointerlockchange", () => {
  if (started && document.pointerLockElement !== canvas && !paused) {
    paused = true;
    pauseScreen.classList.add("open");
  }
});
document.addEventListener("mousemove", (event) => {
  if (document.pointerLockElement === canvas && started && !paused) {
    yaw -= event.movementX * 0.002;
    pitch -= event.movementY * 0.002;
    pitch = Math.max(-1.45, Math.min(1.45, pitch));
  }
});
canvas.addEventListener("mousedown", (event) => {
  if (event.button === 0) raycastPlace(0);
  if (event.button === 2) raycastPlace(2);
});
canvas.addEventListener("contextmenu", (event) => event.preventDefault());

document.addEventListener("keydown", (event) => {
  keys.add(event.code);
  if (event.code === "Space" && grounded) {
    event.preventDefault();
    velocityY = 8;
    grounded = false;
  }
  if (event.code === "Escape" && started) {
    paused = !paused;
    pauseScreen.classList.toggle("open", paused);
    if (!paused) canvas.requestPointerLock?.();
  }
  if (/^Digit[1-5]$/.test(event.code)) {
    const slot = document.querySelector(`[data-block]:nth-child(${event.code.slice(-1)})`);
    slot?.click();
  }
});
document.addEventListener("keyup", (event) => keys.delete(event.code));

startButton.addEventListener("click", () => {
  started = true;
  startScreen.style.display = "none";
  canvas.requestPointerLock?.();
});
resumeButton.addEventListener("click", () => {
  paused = false;
  pauseScreen.classList.remove("open");
  canvas.requestPointerLock?.();
});

let touchLook = null;
document.addEventListener("touchstart", (event) => {
  if (event.target === canvas && event.touches.length === 1 && started && !paused) {
    touchLook = { x: event.touches[0].clientX, y: event.touches[0].clientY };
  }
}, { passive: true });
document.addEventListener("touchmove", (event) => {
  if (!touchLook || event.touches.length !== 1) return;
  const touch = event.touches[0];
  yaw -= (touch.clientX - touchLook.x) * 0.006;
  pitch -= (touch.clientY - touchLook.y) * 0.005;
  pitch = Math.max(-1.45, Math.min(1.45, pitch));
  touchLook = { x: touch.clientX, y: touch.clientY };
}, { passive: true });
document.addEventListener("touchend", () => { touchLook = null; }, { passive: true });

document.querySelectorAll(".slot").forEach((slot) => {
  slot.addEventListener("click", () => {
    document.querySelectorAll(".slot").forEach((item) => item.classList.remove("active"));
    slot.classList.add("active");
    selectedBlock = slot.dataset.block;
  });
});

const joystick = document.querySelector("#joystick");
const joystickKnob = document.querySelector("#joystick-knob");
let joystickActive = false;
function updateJoystick(event) {
  if (!joystickActive) return;
  const rect = joystick.getBoundingClientRect();
  const touch = event.touches?.[0] || event;
  let dx = touch.clientX - (rect.left + rect.width / 2);
  let dy = touch.clientY - (rect.top + rect.height / 2);
  const length = Math.hypot(dx, dy);
  const limit = 30;
  if (length > limit) { dx = dx / length * limit; dy = dy / length * limit; }
  joystickKnob.style.transform = `translate(${dx}px, ${dy}px)`;
  mobileTurn = dx / limit;
  mobileForward = -dy / limit;
}
joystick?.addEventListener("pointerdown", (event) => { joystickActive = true; joystick.setPointerCapture(event.pointerId); });
joystick?.addEventListener("pointermove", updateJoystick);
joystick?.addEventListener("pointerup", () => { joystickActive = false; mobileTurn = 0; mobileForward = 0; joystickKnob.style.transform = ""; });
document.querySelector("#mobile-jump")?.addEventListener("pointerdown", () => {
  if (grounded) { velocityY = 8; grounded = false; }
});

let lastTime = performance.now();
function animate(now = performance.now()) {
  requestAnimationFrame(animate);
  const delta = Math.min((now - lastTime) / 1000, 0.05);
  lastTime = now;
  if (started && !paused) updatePlayer(delta);
  clouds.position.x += delta * 0.5;
  if (clouds.position.x > 20) clouds.position.x = -20;
  renderer.render(scene, camera);
  positionLabel.textContent = `X ${Math.round(player.position.x)} · Y ${Math.round(player.position.y)} · Z ${Math.round(player.position.z)}`;
}
animate();

window.addEventListener("resize", () => {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
});
