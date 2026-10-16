"use client"

import * as React from "react"
import { useEffect, useRef } from "react"

const MAX_DPR = 2
const NEAR = 0.1
const FAR = 2000

const RECYCLE_Z = 200
const RESET_Z = -1800
const SPAN = RECYCLE_Z - RESET_Z

const FOG_DENSITY = 0.001

const STREAK_RADIUS_MIN = 6
const STREAK_SPREAD = 760
const STREAK_LEN_MIN = 170
const STREAK_LEN_SPREAD = 420
const STREAK_OPACITY_SCALE = 1.45
const MAX_STREAKS = 3000

const BASE_FLOW = 15 * 2.4 * 60

const CONE_SEGMENTS = 64
const CONE_FAR_Z = -2900
const CONE_NEAR_Z = -10
const CONE_TOTAL = 3000
const CONE_R_FAR = 240
const CONE_R_SPAN = 900 - 240
const CONE_REPEAT_U = 4
const CONE_REPEAT_V = 2
const CONE_SCROLL = 0.0016
const CONE_TINT_MIX = 0.6

const MAX_PALETTE = 8

const DEFAULT_PALETTE = ["#FFFFFF", "#DBEAFE", "#93C5FD", "#60A5FA", "#C7D2FE"]

const LEGACY_RAMP = [0, 0.23, 0.66, 1, 0.35]
const CONE_OPACITY_SCALE = 0.6

const GLOW_Z = -900
const GLOW_HALF = 380
const GLOW_PULSE = 0.06
const GLOW_PULSE_RATE = 1.6

const STEER_MAX_DEG = 12

const CAMERA_GLSL = `
uniform vec2 uSteer;
uniform float uFocal, uAspect, uZA, uZB;

vec3 steerP(vec3 p){
  float cy = cos(uSteer.x), sy = sin(uSteer.x);
  p = vec3(p.x * cy + p.z * sy, p.y, -p.x * sy + p.z * cy);
  float cx = cos(uSteer.y), sx = sin(uSteer.y);
  return vec3(p.x, p.y * cx - p.z * sx, p.y * sx + p.z * cx);
}

vec4 projectP(vec3 p){
  return vec4(p.x * uFocal / uAspect, p.y * uFocal, p.z * uZA + uZB, -p.z);
}

// The vertex stage only hands over the view depth. Fog is FOG_GLSL's job, in the
// fragment stage, because that is where three evaluates FogExp2 -- and the
// difference is not cosmetic: interpolating exp(-(d * density)^2) itself across a
// streak 2000 units long pulls almost the whole on-screen rail down to the FAR
// end's value, so long streaks would read dimmer than short ones.
float depthOf(vec3 p){
  return max(-p.z, 0.0);
}
`

const FOG_GLSL = `
uniform float uFog;

float clarity(float depth){
  float d = depth * uFog;
  return exp(-d * d);
}
`

const STREAK_VS = `
precision highp float;

attribute vec2 a_dir;
attribute float a_rnorm;
attribute float a_z0;
attribute float a_off;
attribute float a_pick;

uniform float uFlow, uSpan, uResetZ, uRadiusMin, uSpread, uLen;
uniform vec3 uPal[${MAX_PALETTE}];
uniform int uPalN;

varying vec3 vTint;
varying float vDepth;
${CAMERA_GLSL}
void main(){
  float r = uRadiusMin + a_rnorm * uSpread;

  float zh = uResetZ + mod(a_z0 + uFlow - uResetZ, uSpan);
  vec3 p = steerP(vec3(a_dir * r, zh + a_off * uLen));

  float slot = floor(a_pick * float(uPalN));
  int idx = int(min(slot, float(uPalN) - 1.0));
  vec3 tint = uPal[0];
  for (int i = 1; i < ${MAX_PALETTE}; i += 1) {
    if (i == idx) tint = uPal[i];
  }
  vTint = tint;
  vDepth = depthOf(p);
  gl_Position = projectP(p);
}
`

const ADDITIVE_FS = `
precision highp float;
uniform float uOpacity;
${FOG_GLSL}varying vec3 vTint;
varying float vDepth;
void main(){
  float a = uOpacity * clarity(vDepth);
  gl_FragColor = vec4(vTint * a, a);
}
`

const CONE_VS = `
precision highp float;

attribute vec3 a_pos;
attribute vec2 a_uv;

uniform float uRoll, uOffY;
uniform vec2 uRepeat;

varying vec2 vUv;
varying float vDepth;
${CAMERA_GLSL}
void main(){
  float c = cos(uRoll), s = sin(uRoll);
  vec3 p = steerP(vec3(a_pos.x * c - a_pos.y * s, a_pos.x * s + a_pos.y * c, a_pos.z));
  vUv = a_uv * uRepeat + vec2(0.0, uOffY);
  vDepth = depthOf(p);
  gl_Position = projectP(p);
}
`

const CONE_FS = `
precision highp float;
uniform sampler2D uTex;
uniform vec3 uTint;
uniform float uOpacity;
${FOG_GLSL}varying vec2 vUv;
varying float vDepth;
void main(){
  float m = texture2D(uTex, vUv).r;
  float a = m * uOpacity * clarity(vDepth);
  gl_FragColor = vec4(uTint * a, a);
}
`

const GLOW_VS = `
precision highp float;

attribute vec2 a_corner;

uniform float uHalf, uZ;

varying vec2 vUv;
varying float vDepth;
${CAMERA_GLSL}
void main(){
  vec3 p = steerP(vec3(a_corner * uHalf, uZ));
  vUv = a_corner * 0.5 + 0.5;
  vDepth = depthOf(p);
  gl_Position = projectP(p);
}
`

const GLOW_FS = `
precision highp float;
uniform sampler2D uTex;
uniform vec3 uTint;
uniform float uOpacity;
${FOG_GLSL}varying vec2 vUv;
varying float vDepth;
void main(){
  float m = texture2D(uTex, vUv).r;
  float a = m * uOpacity * clarity(vDepth);
  gl_FragColor = vec4(uTint * a, a);
}
`

function compile(gl: WebGLRenderingContext, type: number, src: string): WebGLShader | null {
    const sh = gl.createShader(type)
    if (!sh) return null
    gl.shaderSource(sh, src)
    gl.compileShader(sh)
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error("Hyperspace shader:", gl.getShaderInfoLog(sh))
        gl.deleteShader(sh)
        return null
    }
    return sh
}

function link(gl: WebGLRenderingContext, vsSrc: string, fsSrc: string): WebGLProgram | null {
    const vs = compile(gl, gl.VERTEX_SHADER, vsSrc)
    const fs = compile(gl, gl.FRAGMENT_SHADER, fsSrc)
    if (!vs || !fs) return null
    const prog = gl.createProgram()
    if (!prog) return null
    gl.attachShader(prog, vs)
    gl.attachShader(prog, fs)
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
        console.error("Hyperspace link:", gl.getProgramInfoLog(prog))
        return null
    }
    return prog
}

function uniformCache(gl: WebGLRenderingContext, prog: WebGLProgram) {
    const locs: Record<string, WebGLUniformLocation | null> = {}
    return (name: string) => {
        if (!(name in locs)) locs[name] = gl.getUniformLocation(prog, name)
        return locs[name]
    }
}

type RGBA = [number, number, number, number]

function parseColor(input: string | undefined, fb: RGBA): RGBA {
    if (!input) return fb
    const str = String(input).trim()
    if (str.charAt(0) === "#") {
        let hex = str.slice(1)
        if (hex.length === 3 || hex.length === 4) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2] + (hex.length === 4 ? hex[3] + hex[3] : "")
        }
        if (hex.length >= 6) {
            const r = parseInt(hex.slice(0, 2), 16)
            const g = parseInt(hex.slice(2, 4), 16)
            const b = parseInt(hex.slice(4, 6), 16)
            const a = hex.length >= 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1
            if (!isNaN(r) && !isNaN(g) && !isNaN(b)) return [r / 255, g / 255, b / 255, a]
        }
        return fb
    }
    const m = str.match(/[\d.]+/g)
    if (m && m.length >= 3) {
        return [
            Math.min(255, parseFloat(m[0])) / 255,
            Math.min(255, parseFloat(m[1])) / 255,
            Math.min(255, parseFloat(m[2])) / 255,
            m.length >= 4 ? Math.min(1, parseFloat(m[3])) : 1,
        ]
    }
    return fb
}

function fillPalette(list: unknown, base: string, accent: string, out: Float32Array): number {
    const picked: string[] = Array.isArray(list)
        ? (list as unknown[]).filter((c): c is string => typeof c === "string" && c.length > 0)
        : []
    if (picked.length > 0) {
        const n = Math.min(MAX_PALETTE, picked.length)
        for (let i = 0; i < n; i += 1) {
            const c = parseColor(picked[i], [1, 1, 1, 1])
            out[i * 3] = c[0]
            out[i * 3 + 1] = c[1]
            out[i * 3 + 2] = c[2]
        }
        return n
    }
    const b = parseColor(base, [1, 1, 1, 1])
    const a = parseColor(accent, [0.376, 0.647, 0.98, 1])
    for (let i = 0; i < LEGACY_RAMP.length; i += 1) {
        const t = LEGACY_RAMP[i]
        out[i * 3] = b[0] + (a[0] - b[0]) * t
        out[i * 3 + 1] = b[1] + (a[1] - b[1]) * t
        out[i * 3 + 2] = b[2] + (a[2] - b[2]) * t
    }
    return LEGACY_RAMP.length
}

function num(v: unknown, fb: number): number {
    return typeof v === "number" && isFinite(v) ? v : fb
}

function clampN(v: number, lo: number, hi: number): number {
    return v < lo ? lo : v > hi ? hi : v
}

function mulberry32(seed: number) {
    let a = seed >>> 0
    return () => {
        a = (a + 0x6d2b79f5) >>> 0
        let t = Math.imul(a ^ (a >>> 15), 1 | a)
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    }
}

function makeWallTexture(rand: () => number): HTMLCanvasElement {
    const size = 512
    const c = document.createElement("canvas")
    c.width = size
    c.height = size
    const ctx = c.getContext("2d")
    if (!ctx) return c
    ctx.fillStyle = "#000000"
    ctx.fillRect(0, 0, size, size)
    for (let i = 0; i < 240; i += 1) {
        const x = rand() * size
        const w = rand() * 3 + 0.6
        const h = rand() * 320 + 90
        const top = rand() * size
        const alpha = rand() * 0.45 + 0.08
        for (const offset of [-size, 0, size]) {
            const g = ctx.createLinearGradient(0, top + offset, 0, top + offset + h)
            g.addColorStop(0, "rgba(255,255,255,0)")
            g.addColorStop(0.5, "rgba(255,255,255," + alpha.toFixed(3) + ")")
            g.addColorStop(1, "rgba(255,255,255,0)")
            ctx.fillStyle = g
            ctx.fillRect(x, top + offset, w, h)
        }
    }
    return c
}

function makeGlowTexture(): HTMLCanvasElement {
    const size = 256
    const c = document.createElement("canvas")
    c.width = size
    c.height = size
    const ctx = c.getContext("2d")
    if (!ctx) return c
    ctx.fillStyle = "#000000"
    ctx.fillRect(0, 0, size, size)
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
    g.addColorStop(0, "rgba(255,255,255,1)")
    g.addColorStop(0.18, "rgba(255,255,255,0.55)")
    g.addColorStop(0.45, "rgba(255,255,255,0.16)")
    g.addColorStop(1, "rgba(255,255,255,0)")
    ctx.fillStyle = g
    ctx.fillRect(0, 0, size, size)
    return c
}

function uploadTexture(
    gl: WebGLRenderingContext,
    source: HTMLCanvasElement,
    repeat: boolean
): WebGLTexture | null {
    const tex = gl.createTexture()
    if (!tex) return null
    gl.bindTexture(gl.TEXTURE_2D, tex)

    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source)
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 0)
    const wrap = repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    if (repeat) {
        gl.generateMipmap(gl.TEXTURE_2D)
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
    } else {
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    }
    return tex
}

type Streaks = { length?: number; spread?: number; opacity?: number }
type Tunnel = { opacity?: number; roll?: number; glow?: string }
type Pointer = { steer?: number; boost?: number; damping?: number }

const STREAK_DEFAULTS: Required<Streaks> = { length: 29, spread: 135, opacity: 100 }
const TUNNEL_DEFAULTS: Required<Tunnel> = { opacity: 100, roll: 90, glow: "#7464FFE6" }
const POINTER_DEFAULTS: Required<Pointer> = { steer: 200, boost: 300, damping: 100 }

interface Props {
    style?: React.CSSProperties
    width?: number
    height?: number
    background?: string
    colors?: string[]

    baseColor?: string
    accentColor?: string
    density?: number
    speed?: number
    perspective?: number
    streaks?: Streaks
    tunnel?: Tunnel
    pointer?: Pointer
}

function __OriginkitBase_Hyperspace(props: Props) {
    const {
        style,
        background = "#01020A",
        colors = ["#0047FF", "#FFF000", "#FF6800", "#00FFA8", "#C7D2FE"],
        baseColor = "#FFFFFF",
        accentColor = "#60A5FA",
        density = 880,
        speed = 35,
        perspective = 104,
        streaks,
        tunnel,
        pointer,
        width,
        height,
    } = props

    const streaks_ = { ...STREAK_DEFAULTS, ...(streaks || {}) }
    const tunnel_ = { ...TUNNEL_DEFAULTS, ...(tunnel || {}) }
    const pointer_ = { ...POINTER_DEFAULTS, ...(pointer || {}) }

    const canvasRef = useRef<HTMLCanvasElement>(null)
    const sizeRef = useRef({ w: 0, h: 0 })
    sizeRef.current = { w: num(width, 0), h: num(height, 0) }

    const vRef = useRef<Record<string, number | string | string[] | undefined>>({})
    vRef.current = {
        bg: background,
        pal: colors,
        base: baseColor,
        accent: accentColor,
        streakCount: Math.round(clampN(num(density, 1200), 100, MAX_STREAKS)),
        flow: BASE_FLOW * (clampN(num(speed, 50), 0, 100) / 50),
        fov: clampN(num(perspective, 75), 10, 120),
        len: clampN(num(streaks_.length, 100), 10, 400) / 100,
        spread: (clampN(num(streaks_.spread, 100), 10, 300) / 100) * STREAK_SPREAD,
        streakOpacity: (clampN(num(streaks_.opacity, 60), 0, 100) / 100) * STREAK_OPACITY_SCALE,
        wallOpacity: (clampN(num(tunnel_.opacity, 90), 0, 100) / 100) * CONE_OPACITY_SCALE,
        roll: (clampN(num(tunnel_.roll, 6), -90, 90) * Math.PI) / 180,
        glow: tunnel_.glow,
        steer: (clampN(num(pointer_.steer, 100), 0, 200) / 100) * ((STEER_MAX_DEG * Math.PI) / 180),
        boost: clampN(num(pointer_.boost, 100), 0, 300) / 100,
        damping: clampN(num(pointer_.damping, 30), 1, 100),
    }

    const ptrRef = useRef({ x: 0, y: 0, down: false })

    useEffect(() => {
        const canvas = canvasRef.current
        if (!canvas) return
        const gl = canvas.getContext("webgl", {
            alpha: false,
            antialias: true,
            depth: false,
            powerPreference: "high-performance",
        })
        if (!gl) {
            console.error("Hyperspace: WebGL unavailable")
            return
        }

        const streakProg = link(gl, STREAK_VS, ADDITIVE_FS)
        const coneProg = link(gl, CONE_VS, CONE_FS)
        const glowProg = link(gl, GLOW_VS, GLOW_FS)
        if (!streakProg || !coneProg || !glowProg) return
        const su = uniformCache(gl, streakProg)
        const cu = uniformCache(gl, coneProg)
        const gu = uniformCache(gl, glowProg)

        const rand = mulberry32(0x5eed17)

        const S_STRIDE = 6
        const streakData = new Float32Array(MAX_STREAKS * 2 * S_STRIDE)
        {
            for (let i = 0; i < MAX_STREAKS; i += 1) {
                const angle = rand() * Math.PI * 2
                const rnorm = rand()
                const z0 = (rand() - 0.5) * 2000
                const len = rand() * STREAK_LEN_SPREAD + STREAK_LEN_MIN

                const pick = rand()
                const dx = Math.cos(angle)
                const dy = Math.sin(angle)
                for (let e = 0; e < 2; e += 1) {
                    const o = (i * 2 + e) * S_STRIDE
                    streakData[o] = dx
                    streakData[o + 1] = dy
                    streakData[o + 2] = rnorm
                    streakData[o + 3] = z0
                    streakData[o + 4] = e === 0 ? 0 : len

                    streakData[o + 5] = pick
                }
            }
        }
        const streakBuf = gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER, streakBuf)
        gl.bufferData(gl.ARRAY_BUFFER, streakData, gl.STATIC_DRAW)

        const C_STRIDE = 5
        const coneVerts = CONE_SEGMENTS * 6
        const coneData = new Float32Array(coneVerts * C_STRIDE)
        {
            const vFar = 0
            const vNear = (CONE_NEAR_Z - CONE_FAR_Z) / CONE_TOTAL
            const rFar = CONE_R_FAR + vFar * CONE_R_SPAN
            const rNear = CONE_R_FAR + vNear * CONE_R_SPAN
            let o = 0
            const put = (i: number, nearEnd: boolean) => {
                const u = i / CONE_SEGMENTS
                const theta = u * Math.PI * 2
                const r = nearEnd ? rNear : rFar

                coneData[o] = r * Math.sin(theta)
                coneData[o + 1] = -r * Math.cos(theta)
                coneData[o + 2] = nearEnd ? CONE_NEAR_Z : CONE_FAR_Z
                coneData[o + 3] = u
                coneData[o + 4] = nearEnd ? vNear : vFar
                o += C_STRIDE
            }
            for (let i = 0; i < CONE_SEGMENTS; i += 1) {
                put(i, false)
                put(i + 1, false)
                put(i + 1, true)
                put(i, false)
                put(i + 1, true)
                put(i, true)
            }
        }
        const coneBuf = gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER, coneBuf)
        gl.bufferData(gl.ARRAY_BUFFER, coneData, gl.STATIC_DRAW)

        const glowBuf = gl.createBuffer()
        gl.bindBuffer(gl.ARRAY_BUFFER, glowBuf)
        gl.bufferData(
            gl.ARRAY_BUFFER,
            new Float32Array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1]),
            gl.STATIC_DRAW
        )

        const wallTex = uploadTexture(gl, makeWallTexture(rand), true)
        const glowTex = uploadTexture(gl, makeGlowTexture(), false)

        const bindAttribs = (prog: WebGLProgram, names: string[], sizes: number[], stride: number) => {
            let offset = 0
            const used: number[] = []
            for (let i = 0; i < names.length; i += 1) {
                const loc = gl.getAttribLocation(prog, names[i])
                if (loc >= 0) {
                    gl.enableVertexAttribArray(loc)
                    gl.vertexAttribPointer(loc, sizes[i], gl.FLOAT, false, stride * 4, offset * 4)
                    used.push(loc)
                }
                offset += sizes[i]
            }
            return used
        }

        const palBuf = new Float32Array(MAX_PALETTE * 3)

        let raf = 0
        let last = performance.now()
        let flow = 0
        let clock = 0
        let rollAngle = 0
        let offY = 0
        let steerX = 0
        let steerY = 0
        let boostNow = 1

        const render = (now: number) => {
            const dt = Math.min(0.05, (now - last) / 1000)
            last = now
            const v = vRef.current
            const p = ptrRef.current

            const k = 1 - Math.exp(-(v.damping as number) * 0.12 * dt)
            const boostTarget = p.down ? 1 + (v.boost as number) : 1
            boostNow += (boostTarget - boostNow) * k
            steerX += (-p.x * (v.steer as number) - steerX) * k
            steerY += (p.y * (v.steer as number) - steerY) * k

            const step = (v.flow as number) * boostNow * dt

            flow = (flow + step) % SPAN
            offY = (offY - step * CONE_SCROLL) % 1
            rollAngle = (rollAngle + (v.roll as number) * dt) % (Math.PI * 2)
            clock += dt

            const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR)
            const cw = sizeRef.current.w || canvas.clientWidth || 1200
            const ch = sizeRef.current.h || canvas.clientHeight || 800
            const bw = Math.max(1, Math.round(cw * dpr))
            const bh = Math.max(1, Math.round(ch * dpr))
            if (canvas.width !== bw || canvas.height !== bh) {
                canvas.width = bw
                canvas.height = bh
            }
            gl.viewport(0, 0, bw, bh)

            const bg = parseColor(v.bg as string, [0.004, 0.008, 0.039, 1])
            const glow = parseColor(v.glow as string, [0.859, 0.918, 0.996, 0.9])
            const palN = fillPalette(v.pal, v.base as string, v.accent as string, palBuf)

            const w1 = palN > 1 ? 3 : 0

            gl.clearColor(bg[0], bg[1], bg[2], 1)
            gl.clear(gl.COLOR_BUFFER_BIT)
            gl.disable(gl.DEPTH_TEST)

            gl.disable(gl.CULL_FACE)
            gl.enable(gl.BLEND)
            gl.blendFunc(gl.ONE, gl.ONE)

            const focal = 1 / Math.tan((((v.fov as number) * Math.PI) / 180) / 2)
            const aspect = bw / Math.max(1, bh)
            const zA = (FAR + NEAR) / (NEAR - FAR)
            const zB = (2 * FAR * NEAR) / (NEAR - FAR)

            const camera = (u: (n: string) => WebGLUniformLocation | null) => {
                gl.uniform2f(u("uSteer"), steerX, steerY)
                gl.uniform1f(u("uFocal"), focal)
                gl.uniform1f(u("uAspect"), aspect)
                gl.uniform1f(u("uZA"), zA)
                gl.uniform1f(u("uZB"), zB)
                gl.uniform1f(u("uFog"), FOG_DENSITY)
            }

            if (wallTex) {
                gl.useProgram(coneProg)
                gl.bindBuffer(gl.ARRAY_BUFFER, coneBuf)
                const cAttribs = bindAttribs(coneProg, ["a_pos", "a_uv"], [3, 2], C_STRIDE)
                camera(cu)
                gl.activeTexture(gl.TEXTURE0)
                gl.bindTexture(gl.TEXTURE_2D, wallTex)
                gl.uniform1i(cu("uTex"), 0)
                gl.uniform1f(cu("uRoll"), rollAngle)
                gl.uniform1f(cu("uOffY"), offY)
                gl.uniform2f(cu("uRepeat"), CONE_REPEAT_U, CONE_REPEAT_V)
                gl.uniform1f(cu("uOpacity"), v.wallOpacity as number)
                gl.uniform3f(
                    cu("uTint"),
                    palBuf[0] + (palBuf[w1] - palBuf[0]) * CONE_TINT_MIX,
                    palBuf[1] + (palBuf[w1 + 1] - palBuf[1]) * CONE_TINT_MIX,
                    palBuf[2] + (palBuf[w1 + 2] - palBuf[2]) * CONE_TINT_MIX
                )
                gl.drawArrays(gl.TRIANGLES, 0, coneVerts)
                for (const loc of cAttribs) gl.disableVertexAttribArray(loc)
            }

            if (glowTex && glow[3] > 0) {
                gl.useProgram(glowProg)
                gl.bindBuffer(gl.ARRAY_BUFFER, glowBuf)
                const gAttribs = bindAttribs(glowProg, ["a_corner"], [2], 2)
                camera(gu)
                gl.activeTexture(gl.TEXTURE0)
                gl.bindTexture(gl.TEXTURE_2D, glowTex)
                gl.uniform1i(gu("uTex"), 0)
                gl.uniform1f(gu("uHalf"), GLOW_HALF * (1 + Math.sin(clock * GLOW_PULSE_RATE) * GLOW_PULSE))
                gl.uniform1f(gu("uZ"), GLOW_Z)
                gl.uniform1f(gu("uOpacity"), glow[3])
                gl.uniform3f(gu("uTint"), glow[0], glow[1], glow[2])
                gl.drawArrays(gl.TRIANGLES, 0, 6)
                for (const loc of gAttribs) gl.disableVertexAttribArray(loc)
            }

            gl.useProgram(streakProg)
            gl.bindBuffer(gl.ARRAY_BUFFER, streakBuf)
            const sAttribs = bindAttribs(
                streakProg,
                ["a_dir", "a_rnorm", "a_z0", "a_off", "a_pick"],
                [2, 1, 1, 1, 1],
                S_STRIDE
            )
            camera(su)
            gl.uniform1f(su("uFlow"), flow)
            gl.uniform1f(su("uSpan"), SPAN)
            gl.uniform1f(su("uResetZ"), RESET_Z)
            gl.uniform1f(su("uRadiusMin"), STREAK_RADIUS_MIN)
            gl.uniform1f(su("uSpread"), v.spread as number)

            gl.uniform1f(su("uLen"), (v.len as number) * Math.sqrt(boostNow))
            gl.uniform1f(su("uOpacity"), v.streakOpacity as number)

            gl.uniform3fv(su("uPal[0]"), palBuf)
            gl.uniform1i(su("uPalN"), palN)
            gl.drawArrays(gl.LINES, 0, (v.streakCount as number) * 2)
            for (const loc of sAttribs) gl.disableVertexAttribArray(loc)

            raf = requestAnimationFrame(render)
        }

        const track = (e: PointerEvent) => {
            const w = window.innerWidth || canvas.clientWidth || 1200
            const h = window.innerHeight || canvas.clientHeight || 800
            ptrRef.current.x = (e.clientX / w) * 2 - 1
            ptrRef.current.y = 1 - (e.clientY / h) * 2
        }
        const onLeave = () => {
            ptrRef.current.x = 0
            ptrRef.current.y = 0
            ptrRef.current.down = false
        }
        const onDown = (e: PointerEvent) => {
            track(e)
            ptrRef.current.down = true
        }

        const onUp = () => {
            ptrRef.current.down = false
        }

        window.addEventListener("pointermove", track)
        window.addEventListener("pointerdown", onDown)
        window.addEventListener("pointerup", onUp)
        window.addEventListener("pointercancel", onUp)
        document.addEventListener("mouseleave", onLeave)

        raf = requestAnimationFrame(render)

        return () => {
            cancelAnimationFrame(raf)
            window.removeEventListener("pointermove", track)
            window.removeEventListener("pointerdown", onDown)
            window.removeEventListener("pointerup", onUp)
            window.removeEventListener("pointercancel", onUp)
            document.removeEventListener("mouseleave", onLeave)
        }
    }, [])

    return (
        <div
            style={{
                position: "relative",
                overflow: "hidden",
                background,
                isolation: "isolate",
                minWidth: 0,
                minHeight: 0,
                width: typeof width === "number" && width > 0 ? width : "100%",
                height: typeof height === "number" && height > 0 ? height : "100%",
                ...style,
            }}
        >
            <canvas
                ref={canvasRef}
                style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    display: "block",
                }}
            />
        </div>
    )
}

const __originkitPresetProps = {
  "background": "#01020A",
  "colors": [
    "#0047FF",
    "#C7D2FE",
    "#000000"
  ],
  "density": 260,
  "speed": 18,
  "perspective": 78,
  "streaks": {
    "length": 29,
    "spread": 135,
    "opacity": 100
  },
  "tunnel": {
    "glow": "#7464FFE6",
    "roll": 90,
    "opacity": 100
  },
  "pointer": {
    "boost": 135,
    "steer": 200,
    "damping": 100
  }
};

export default function Hyperspace(props: Record<string, unknown>) {
  return <__OriginkitBase_Hyperspace {...(__originkitPresetProps as Record<string, unknown>)} {...props} />;
}