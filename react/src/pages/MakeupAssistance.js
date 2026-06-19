import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles, Upload, Home, RotateCcw, CheckCircle2,
  Eye, Smile, Palette, Star, Feather, Layers, ArrowRight,
  Camera, Wand2, ChevronDown, ChevronUp, ImageIcon, Scissors, X, Video,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import NearbyProvidersMap from '../components/NearbyProvidersMap';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './MakeupAssistance.css';

/* ─── Event types ────────────────────────────────────────────────── */
const EVENT_TYPES = [
  { id: 'formal',       label: 'Formal',       emoji: '🎩' },
  { id: 'casual_soft',  label: 'Casual Soft',  emoji: '🌸' },
  { id: 'casual_glam',  label: 'Casual Glam',  emoji: '✨' },
  { id: 'party',        label: 'Party',        emoji: '🎉' },
  { id: 'wedding',      label: 'Wedding',      emoji: '💍' },
  { id: 'office',       label: 'Office Look',  emoji: '💼' },
  { id: 'other',        label: 'Other',        emoji: '🎨' },
];

/* ─── Mock AI recommendations keyed by event ────────────────────── */
const RECOMMENDATIONS = {
  formal: {
    palette: 'Classic & Polished',
    foundation: {
      shade: 'Medium-full coverage', tip: 'Use a satin or semi-matte foundation for a long-lasting sophisticated finish. Set with translucent powder.',
      shades: [{ name: 'Natural Beige', color: '#D4A574' }, { name: 'Warm Ivory', color: '#F5DEB3' }],
    },
    eyes: {
      shade: 'Smokey charcoal & champagne', tip: 'Apply a deep charcoal to the crease and outer-V, champagne shimmer on the lid. Wing liner adds drama.',
      shades: [{ name: 'Charcoal', color: '#36454F' }, { name: 'Champagne', color: '#F7E7CE' }],
    },
    lips: {
      shade: 'Classic red or deep berry', tip: 'A bold lip anchors a formal look. Line with a matching liner and blot once for longevity.',
      shades: [{ name: 'Classic Red', color: '#B22222' }, { name: 'Deep Berry', color: '#8B1A4A' }],
    },
    blush: {
      shade: 'Rose or dusty mauve', tip: 'Sweep blush along the cheekbones from temple downward in a "C" shape for sculpted elegance.',
      shades: [{ name: 'Dusty Rose', color: '#C4788A' }, { name: 'Mauve', color: '#9C687F' }],
    },
    contour: {
      shade: 'Cool-toned taupe', tip: 'Contour under cheekbones, along the jawline and sides of the nose. Blend thoroughly.',
      shades: [{ name: 'Cool Taupe', color: '#7D6B5D' }],
    },
    eyeliner: {
      shade: 'Jet black gel', tip: 'A tight upper waterline line + extended wing creates a polished, elongated eye.',
      shades: [{ name: 'Jet Black', color: '#1C1C1C' }],
    },
    brows: {
      shade: 'Dark brown or ebony', tip: 'Define and fill sparse areas. Use a brow gel for all-day hold at a formal event.',
      shades: [{ name: 'Dark Brown', color: '#5C3D2E' }],
    },
    highlighter: {
      shade: 'Pearl white or gold', tip: "Apply to the brow bone, inner corner and cupid’s bow for a luminous, polished glow.",
      shades: [{ name: 'Pearl', color: '#FDEBD0' }, { name: 'Gold', color: '#D4AF37' }],
    },
  },
  casual_soft: {
    palette: 'Fresh & Natural',
    foundation: {
      shade: 'Light, skin-like coverage', tip: 'BB cream or light-coverage foundation keeps the look fresh. Spot-conceal only where needed.',
      shades: [{ name: 'Nude', color: '#E8C9A0' }, { name: 'Porcelain', color: '#FAE5CA' }],
    },
    eyes: {
      shade: 'Warm peach & soft brown', tip: 'Blend a peachy-nude on the lid and a soft brown in the crease for gentle dimension.',
      shades: [{ name: 'Soft Peach', color: '#FFCBA4' }, { name: 'Warm Brown', color: '#A0785A' }],
    },
    lips: {
      shade: 'MLBB nude or sheer pink', tip: 'A tinted lip balm or sheer gloss gives effortless, everyday appeal.',
      shades: [{ name: 'MLBB Nude', color: '#C68B6E' }, { name: 'Sheer Pink', color: '#F4A7A7' }],
    },
    blush: {
      shade: 'Peach or coral', tip: 'Smile and dust blush on the apples of cheeks, blending upward for a youthful flush.',
      shades: [{ name: 'Coral Peach', color: '#FF7F60' }, { name: 'Soft Coral', color: '#F08070' }],
    },
    contour: {
      shade: 'Light bronzer', tip: 'Dust bronzer lightly around the perimeter of the face for a sun-kissed, natural warmth.',
      shades: [{ name: 'Light Bronze', color: '#C68642' }],
    },
    eyeliner: {
      shade: 'Brown or nude', tip: 'Skip heavy liner. A thin brown line close to lashes or a subtle nude waterline brightens the eye.',
      shades: [{ name: 'Warm Brown', color: '#5E3B2A' }, { name: 'Nude', color: '#D4B09A' }],
    },
    brows: {
      shade: 'Soft taupe', tip: 'Brush and lightly fill — aim for "your brows but better." Keep arches natural.',
      shades: [{ name: 'Soft Taupe', color: '#8C7B6E' }],
    },
    highlighter: {
      shade: 'Dewy peach', tip: 'Press a liquid highlighter onto the high points for a glass-skin glow.',
      shades: [{ name: 'Dewy Peach', color: '#FFC499' }],
    },
  },
  casual_glam: {
    palette: 'Effortless Glam',
    foundation: {
      shade: 'Medium coverage with glow', tip: 'Use a dewy foundation for luminosity. Add a liquid highlighter mixed in for extra radiance.',
      shades: [{ name: 'Golden Beige', color: '#D2935F' }, { name: 'Warm Sand', color: '#ECC88A' }],
    },
    eyes: {
      shade: 'Bronze & copper shimmer', tip: 'Pack copper shimmer on the lid, brown to deepen the crease. Add lower lash shimmer for intensity.',
      shades: [{ name: 'Bronze', color: '#CD7F32' }, { name: 'Copper', color: '#B87333' }],
    },
    lips: {
      shade: 'Terracotta or burnt rose', tip: 'A satin terracotta keeps glam elevated but wearable. Line slightly outside natural lip line for fullness.',
      shades: [{ name: 'Terracotta', color: '#C05C35' }, { name: 'Burnt Rose', color: '#B04060' }],
    },
    blush: {
      shade: 'Warm peach-bronze', tip: 'Blend onto cheekbones and lightly onto temples to complement the bronzy eye.',
      shades: [{ name: 'Warm Peach', color: '#FFAB76' }],
    },
    contour: {
      shade: 'Warm chestnut', tip: 'Sculpt cheekbones, jawline and nose — warm tones blend seamlessly for casual glam.',
      shades: [{ name: 'Chestnut', color: '#954535' }],
    },
    eyeliner: {
      shade: 'Bronze or dark brown', tip: 'Smudge along upper lash line for a sultry, undone glam effect.',
      shades: [{ name: 'Bronze Liner', color: '#8C6239' }],
    },
    brows: {
      shade: 'Medium brown', tip: 'Fluffy, brushed-up brows balance the glam eye. Use a tinted brow gel.',
      shades: [{ name: 'Medium Brown', color: '#7B4F2E' }],
    },
    highlighter: {
      shade: 'Rose gold', tip: 'Dust rose gold on cheekbones, collar bone and brow arch for runway-worthy luminosity.',
      shades: [{ name: 'Rose Gold', color: '#B76E79' }],
    },
  },
  party: {
    palette: 'Bold & Vivid',
    foundation: {
      shade: 'Full coverage, matte', tip: 'Lock everything in with a full-coverage primer + matte foundation. Use setting spray for all-night hold.',
      shades: [{ name: 'Warm Tan', color: '#C19A6B' }],
    },
    eyes: {
      shade: 'Jewel tones — sapphire, emerald or amethyst', tip: 'Go bold with a pop of jewel-toned eyeshadow. Add glitter in the inner corner.',
      shades: [{ name: 'Sapphire', color: '#0F52BA' }, { name: 'Amethyst', color: '#9966CC' }, { name: 'Emerald', color: '#50C878' }],
    },
    lips: {
      shade: 'Hot pink, fuchsia or flame', tip: 'Pair bold eyes with a satin-finish bright lip. Use long-wear formula for dancing the night away.',
      shades: [{ name: 'Hot Pink', color: '#FF69B4' }, { name: 'Flame Red', color: '#FF4500' }],
    },
    blush: {
      shade: 'Electric pink or fuchsia', tip: 'High-pigment blush gives a flush that photographs beautifully under party lighting.',
      shades: [{ name: 'Electric Pink', color: '#FF007F' }],
    },
    contour: {
      shade: 'Deep cool brown', tip: 'Sharpen the face for dramatic party lighting with a deep contour. Blend well.',
      shades: [{ name: 'Deep Brown', color: '#5B3427' }],
    },
    eyeliner: {
      shade: 'Glitter or neon liner', tip: 'A graphic liner or pop of neon on the waterline makes eyes pop under club lighting.',
      shades: [{ name: 'Glitter', color: '#C0C0C0' }, { name: 'Neon', color: '#CCFF00' }],
    },
    brows: {
      shade: 'Bold and defined', tip: 'Fill brows fully and set with clear gel. Defined brows frame bold party looks.',
      shades: [{ name: 'Ebony', color: '#3B2314' }],
    },
    highlighter: {
      shade: 'Blinding chrome or holographic', tip: 'A duo-chrome or holographic highlighter on the high points creates a dazzling club effect.',
      shades: [{ name: 'Chrome', color: '#E8E8E8' }, { name: 'Holo', color: '#B5A8D0' }],
    },
  },
  wedding: {
    palette: 'Romantic & Luminous',
    foundation: {
      shade: 'Flawless medium-full coverage', tip: 'Choose a long-wear foundation with a radiant finish. Prime well and set with a setting spray for 12+ hour wear.',
      shades: [{ name: 'Ivory', color: '#F4ECD8' }, { name: 'Warm Beige', color: '#E0C49A' }],
    },
    eyes: {
      shade: 'Champagne, rose gold, soft taupe', tip: 'Layer a romantic rose-gold shimmer on the lid with a soft taupe crease. Lush false lashes complete the bridal eye.',
      shades: [{ name: 'Rose Gold', color: '#B76E79' }, { name: 'Soft Taupe', color: '#9E8B7B' }],
    },
    lips: {
      shade: 'Dusty rose, blush pink or classic red', tip: 'Pick a shade that photographs well. Blot and re-apply in layers for a kiss-proof finish.',
      shades: [{ name: 'Blush Pink', color: '#FFB6C1' }, { name: 'Dusty Rose', color: '#D8A0A0' }],
    },
    blush: {
      shade: 'Soft rose or ballet pink', tip: 'Drape blush gently from cheekbones upward toward temples — a romantic, lifted effect.',
      shades: [{ name: 'Ballet Pink', color: '#FADADD' }, { name: 'Soft Rose', color: '#E8A0A8' }],
    },
    contour: {
      shade: 'Neutral taupe', tip: 'Keep contouring subtle for wedding photos. A light hand ensures the look stays romantic, not overdone.',
      shades: [{ name: 'Neutral Taupe', color: '#8E7968' }],
    },
    eyeliner: {
      shade: 'Dark brown or black on upper lash line', tip: 'Tight-line the upper lid for definition without heaviness. Waterproof formula is essential.',
      shades: [{ name: 'Soft Black', color: '#2E2E2E' }],
    },
    brows: {
      shade: 'Natural match with fill', tip: 'Well-groomed and filled brows look polished in photos. Tint if needed a few days before.',
      shades: [{ name: 'Natural Fill', color: '#7B5B42' }],
    },
    highlighter: {
      shade: 'Soft pearl & gold', tip: 'A liquid highlighter mixed into foundation + powder highlight on cheekbones gives an ethereal bridal glow.',
      shades: [{ name: 'Pearl', color: '#FDEBD0' }, { name: 'Soft Gold', color: '#D4AF37' }],
    },
  },
  office: {
    palette: 'Clean & Professional',
    foundation: {
      shade: 'Light-medium, matte finish', tip: 'A matte or natural finish keeps the face shine-free through a full workday. Spot-conceal only as needed.',
      shades: [{ name: 'Natural Beige', color: '#D4A574' }, { name: 'Ivory', color: '#F5DEB3' }],
    },
    eyes: {
      shade: 'Neutral taupe & soft brown', tip: 'Keep eye makeup simple — taupe on the lid, soft brown in the crease. Mascara only or a thin liner.',
      shades: [{ name: 'Taupe', color: '#B5A59A' }, { name: 'Soft Brown', color: '#9C7B6D' }],
    },
    lips: {
      shade: 'Nude, mauve or MLBB', tip: 'A polished nude or mauve keeps the professional aesthetic. Opt for a satin finish for all-day comfort.',
      shades: [{ name: 'Nude Mauve', color: '#C4A0A0' }, { name: 'MLBB', color: '#C6836A' }],
    },
    blush: {
      shade: 'Soft peach or nude pink', tip: 'A light touch of blush adds healthy colour without looking overdone in office lighting.',
      shades: [{ name: 'Soft Peach', color: '#FFCBA4' }],
    },
    contour: {
      shade: 'Light bronzer or warm taupe', tip: 'Very light, subtle contouring keeps the office look polished and natural.',
      shades: [{ name: 'Warm Taupe', color: '#A08070' }],
    },
    eyeliner: {
      shade: 'Brown or slate grey', tip: 'A thin line in brown or grey is professional and defined without being too dramatic.',
      shades: [{ name: 'Slate Grey', color: '#708090' }, { name: 'Warm Brown', color: '#5E3B2A' }],
    },
    brows: {
      shade: 'Soft match', tip: 'Clean, well-defined brows signal professionalism. Keep them natural and neat.',
      shades: [{ name: 'Soft Fill', color: '#8C7060' }],
    },
    highlighter: {
      shade: 'Subtle champagne', tip: 'A very light champagne on the brow bone and inner corner is all you need for a fresh office glow.',
      shades: [{ name: 'Champagne', color: '#F7E7CE' }],
    },
  },
};

/* ─── Default for "other" events ─── */
const DEFAULT_REC = RECOMMENDATIONS.casual_glam;

/* ─── Icon + colour mapping per makeup category ─── */
const CARD_META = {
  foundation:  { icon: <Layers size={16}/>,   bg: '#FDE8D8', color: '#C2612A', label: 'Foundation' },
  eyes:        { icon: <Eye size={16}/>,       bg: '#E0F2FE', color: '#0284C7', label: 'Eye Shadow' },
  lips:        { icon: <Smile size={16}/>,     bg: '#FCE7F3', color: '#DB2777', label: 'Lips' },
  blush:       { icon: <Feather size={16}/>,   bg: '#FEE2E2', color: '#DC2626', label: 'Blush' },
  contour:     { icon: <Palette size={16}/>,   bg: '#FEF3C7', color: '#D97706', label: 'Contour' },
  eyeliner:    { icon: <Star size={16}/>,      bg: '#EDE9FE', color: '#7C3AED', label: 'Eyeliner' },
  brows:       { icon: <ArrowRight size={16}/>,bg: '#D1FAE5', color: '#059669', label: 'Brows' },
  highlighter: { icon: <Sparkles size={16}/>,  bg: '#FEF9C3', color: '#CA8A04', label: 'Highlighter' },
};

/* ─── Step-by-step guide builder ────────────────────────────────── */
function buildSteps(event, rec) {
  // Defensive reader — if a category is missing or shaped oddly, fall
  // back to placeholder strings instead of throwing on `.shade`/`.tip`.
  const r = rec || {};
  const get = (cat, field, fallback = '') => {
    const obj = r[cat];
    if (obj && typeof obj === 'object' && obj[field]) return obj[field];
    return fallback;
  };

  // Build the step list, then filter out any step whose category is
  // entirely missing so we never render a half-empty card.
  const steps = [
    {
      title: 'Prep & Prime',
      desc: 'Cleanse, moisturise and apply a primer suited to your skin type. Allow 1–2 minutes for primer to set before foundation.',
      tip: 'Hydrated skin gives a smoother, longer-lasting application',
    },
    r.foundation && {
      title: `Apply ${get('foundation', 'shade', 'your')} Foundation`,
      desc:  get('foundation', 'tip', 'Apply foundation evenly with a damp sponge.'),
      tip:  'Use a damp beauty sponge for a seamless, skin-like finish',
    },
    {
      title: 'Conceal & Set',
      desc: 'Spot-conceal blemishes and under-eye circles. Set the T-zone with translucent powder to lock foundation in place.',
      tip:  'Bake under-eyes for a bright, crease-free look',
    },
    r.contour && {
      title: `${get('contour', 'shade', 'Subtle')} Contour`,
      desc:  get('contour', 'tip', 'Lightly sculpt cheekbones, jawline and nose.'),
      tip:  'Always blend with circular motions — no harsh lines',
    },
    r.blush && {
      title: `${get('blush', 'shade', 'Soft')} Blush`,
      desc:  get('blush', 'tip', 'Apply blush to the apples of the cheeks.'),
      tip:  'Smile to find the apple of your cheeks for precise placement',
    },
    r.eyes && {
      title: `Eye Makeup — ${get('eyes', 'shade', 'Neutral')}`,
      desc:  get('eyes', 'tip', 'Blend eyeshadow gradually from lid to crease.'),
      tip:  'Work from lightest to darkest shades — build colour gradually',
    },
    r.eyeliner && {
      title: `Eyeliner: ${get('eyeliner', 'shade', 'Brown or black')}`,
      desc:  get('eyeliner', 'tip', 'Line the upper lash line in a thin, steady stroke.'),
      tip:  'Rest your elbow on a flat surface for a steady, precise hand',
    },
    r.brows && {
      title: 'Brows',
      desc:  get('brows', 'tip', 'Brush brows up and lightly fill sparse areas.'),
      tip:  'Comb upward first, then fill in sparse areas only',
    },
    r.lips && {
      title: `Lips: ${get('lips', 'shade', 'Your shade')}`,
      desc:  get('lips', 'tip', 'Apply lip colour and blot once for longevity.'),
      tip:  'Blot, then reapply for transfer-proof colour',
    },
    r.highlighter && {
      title: `Highlighter: ${get('highlighter', 'shade', 'Subtle glow')}`,
      desc:  get('highlighter', 'tip', 'Tap highlighter onto cheekbones and brow bones.'),
      tip:  'Less is more — build up slowly for a natural glow',
    },
    {
      title: 'Setting Spray',
      desc: `Lock your complete ${event} look with a finishing setting spray. Hold 8–10 inches from the face and mist in a figure-eight motion.`,
      tip:  'Your look is complete — enjoy your event.',
    },
  ];
  return steps.filter(Boolean);
}

/* ─── Loading steps ──────────────────────────────────────────────── */
const LOADING_STEPS = [
  'Detecting facial features…',
  'Analysing skin tone…',
  'Evaluating undertones…',
  'Matching event palette…',
  'Generating shade recommendations…',
  'Building step-by-step guide…',
  'Applying virtual preview…',
  'Finalising your look…',
];

/* ═══════════════════════════════════════════════════════════════════
   Main Component
══════════════════════════════════════════════════════════════════════ */
export default function MakeupAssistance() {
  const navigate = useNavigate();

  /* Upload state */
  const [imgSrc, setImgSrc]       = useState(null);
  const [imgEl,  setImgEl]        = useState(null); // HTMLImageElement
  const [imgFile, setImgFile]     = useState(null); // raw File for upload
  const [dragging, setDragging]   = useState(false);
  const [apiError, setApiError]   = useState('');

  /* Camera */
  const [cameraOpen,   setCameraOpen]   = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [cameraError,  setCameraError]  = useState('');
  const videoRef = useRef(null);

  /* Event selection */
  const [selectedEvent, setSelectedEvent] = useState('');
  const [otherText,     setOtherText]     = useState('');

  /* Analysis state */
  const [phase,    setPhase]    = useState('idle'); // idle | loading | done
  const [progress, setProgress] = useState(0);
  const [stepIdx,  setStepIdx]  = useState(0);

  /* Results */
  const [rec,       setRec]       = useState(null);
  const [showSteps, setShowSteps] = useState(false);

  /* Refs */
  const fileInputRef   = useRef(null);
  const resultsRef     = useRef(null);

  /* ── Handle image file ── */
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
  const loadFile = useCallback((file) => {
    if (!file || !file.type.startsWith('image/')) return;
    // P2 — client-side 10MB guard so users don't wait for upload then 400.
    if (file.size > MAX_UPLOAD_BYTES) {
      setApiError('Image must be under 10 MB. Please pick a smaller file.');
      return;
    }
    setApiError('');
    const url = URL.createObjectURL(file);
    const el  = new Image();
    el.onload = () => { setImgEl(el); setImgSrc(url); setImgFile(file); };
    el.src = url;
  }, []);

  const onFileChange = (e) => loadFile(e.target.files[0]);
  const onDrop       = (e) => { e.preventDefault(); setDragging(false); loadFile(e.dataTransfer.files[0]); };
  const onDragOver   = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave  = () => setDragging(false);

  /* ── Camera ──
     On mobile browsers `navigator.mediaDevices` is undefined when the
     origin is HTTP (insecure). We bail BEFORE touching the API so a
     reference error never leaks to the user — and we surface a clear
     "use Upload Photo instead" fallback hint. */
  const openCamera = async () => {
    setCameraError('');
    const hasSecureContext =
      typeof window !== 'undefined' ? window.isSecureContext !== false : true;
    const hasApi =
      typeof navigator !== 'undefined' &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === 'function';
    if (!hasSecureContext || !hasApi) {
      setCameraError('Camera requires HTTPS or localhost. Use "Choose Photo" to upload instead.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false,
      });
      setCameraStream(stream);
      setCameraOpen(true);
      setTimeout(() => { if (videoRef.current) videoRef.current.srcObject = stream; }, 80);
    } catch (err) {
      const map = {
        NotAllowedError:     'Camera access denied. Allow camera permission and try again.',
        NotFoundError:       'No camera found on this device.',
        NotReadableError:    'Camera is in use by another app.',
        OverconstrainedError:'Camera does not support the requested settings.',
        SecurityError:       'Camera requires HTTPS or localhost.',
      };
      setCameraError(map[err?.name] || `Camera error: ${err?.message || 'unknown'}.`);
    }
  };
  const closeCamera = () => {
    if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());
    setCameraStream(null); setCameraOpen(false); setCameraError('');
  };
  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width  = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
    // Get the captured image as a Blob so we can upload it as a File.
    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
      const url  = URL.createObjectURL(file);
      const el   = new Image();
      el.onload = () => { setImgEl(el); setImgSrc(url); setImgFile(file); };
      el.src = url;
      closeCamera();
    }, 'image/jpeg', 0.92);
  };
  useEffect(() => () => { if (cameraStream) cameraStream.getTracks().forEach(t => t.stop()); }, [cameraStream]);

  /* ── Real backend analysis ── */
  const handleAnalyze = async () => {
    if (!imgSrc || !selectedEvent || !imgFile) return;
    setApiError('');
    setPhase('loading');
    setProgress(0);
    setStepIdx(0);

    // Drive the progress UI while we await the real network call.
    const total = LOADING_STEPS.length;
    let p = 0;
    const tick = setInterval(() => {
      p += Math.random() * 8 + 2;
      if (p > 95) p = 95;            // cap at 95 — real completion bumps to 100
      setProgress(Math.round(p));
      setStepIdx(Math.min(total - 1, Math.floor((p / 100) * total)));
    }, 250);

    try {
      const formData = new FormData();
      formData.append('image', imgFile);
      formData.append('event_type', selectedEvent === 'other'
        ? (otherText.trim() || 'other')
        : selectedEvent);

      const res = await apiClient.post(API_ENDPOINTS.MAKEUP.SUGGEST, formData, {
        headers: { 'Accept': 'application/json' },
        timeout: 180000,
      });

      const data = res.data?.data || res.data || {};
      const suggestions = data.suggestions || data;

      // Backend now returns validated flat strings per category.
      // The frontend visual cards need swatch arrays (.shades[]) which come
      // from the static RECOMMENDATIONS template, while the backend's textual
      // tip is overlaid per category. No defensive shape juggling.
      const baseRec = selectedEvent === 'other'
        ? DEFAULT_REC
        : (RECOMMENDATIONS[selectedEvent] || DEFAULT_REC);

      // Map backend keys → frontend visual categories
      const backendByCategory = {
        eyes:        suggestions.eyeshadow  || suggestions.eyes        || '',
        lips:        suggestions.lipstick   || suggestions.lips        || '',
        blush:       suggestions.blush                                  || '',
        highlighter: suggestions.highlighter || suggestions.glow        || '',
      };

      const adoptTip = (cat) => {
        const baseObj = baseRec[cat] || {};
        const fromBackend = backendByCategory[cat];
        // If backend already gave a proper {shade, shades, tip}, keep it.
        if (fromBackend && typeof fromBackend === 'object' && Array.isArray(fromBackend.shades)) {
          return fromBackend;
        }
        // Otherwise overlay the textual tip onto the template object.
        return {
          ...baseObj,
          tip: typeof fromBackend === 'string' && fromBackend.trim()
                 ? fromBackend
                 : baseObj.tip,
        };
      };

      // Start from the full template so every category referenced by
      // buildSteps / the recommendation grid is present (foundation,
      // contour, eyeliner, brows + the four below). Then overlay the
      // backend tips on top of the four it actually returns.
      const merged = {
        ...baseRec,
        palette:     suggestions.palette || baseRec.palette,
        eyes:        adoptTip('eyes'),
        lips:        adoptTip('lips'),
        blush:       adoptTip('blush'),
        highlighter: adoptTip('highlighter'),
        _serverDetected: {
          face_shape: data.face_shape || null,
          skin_tone:  data.skin_tone  || null,
        },
        _serverRaw: suggestions,
      };

      // Override the template swatches with the backend's skin-tone-derived
      // shades (name + hex) so colours differ by skin tone, not just by event.
      const bShades = suggestions.shades && typeof suggestions.shades === 'object'
        ? suggestions.shades : null;
      if (bShades) {
        ['foundation','eyes','lips','blush','contour','eyeliner','brows','highlighter'].forEach(cat => {
          const arr = bShades[cat]
            || (cat === 'eyes' ? bShades.eyeshadow : null)
            || (cat === 'lips' ? bShades.lipstick  : null);
          if (Array.isArray(arr) && arr.length && merged[cat] && typeof merged[cat] === 'object') {
            const mapped = arr
              .map(s => ({ name: s?.name || 'Shade', color: s?.hex || s?.color }))
              .filter(s => typeof s.color === 'string' && /^#?[0-9a-fA-F]{3,6}$/.test(s.color.trim()))
              .map(s => ({ name: s.name, color: s.color.trim().startsWith('#') ? s.color.trim() : '#' + s.color.trim() }));
            if (mapped.length) merged[cat] = { ...merged[cat], shades: mapped };
          }
        });
      }

      clearInterval(tick);
      setProgress(100);
      setStepIdx(total - 1);
      setRec(merged);
      setPhase('done');
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      clearInterval(tick);
      setApiError(err?.message || 'Analysis failed. Please try again.');
      setPhase('idle');
      setProgress(0);
    }
  };

  /* ── Reset ── */
  const handleReset = () => {
    setPhase('idle'); setImgSrc(null); setImgEl(null); setImgFile(null);
    setSelectedEvent(''); setOtherText(''); setRec(null);
    setShowSteps(false); setProgress(0); setStepIdx(0); setApiError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const eventLabel = selectedEvent === 'other'
    ? (otherText.trim() || 'Custom Event')
    : EVENT_TYPES.find(e => e.id === selectedEvent)?.label || '';

  const canAnalyze = !!imgSrc && !!selectedEvent && (selectedEvent !== 'other' || otherText.trim().length > 0);

  /* ── Steps ── */
  const steps = rec ? buildSteps(eventLabel, rec) : [];

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar />

      {/* Camera Modal */}
      {cameraOpen && (
        <div className="mua-camera-modal-overlay">
          <div className="mua-camera-modal">
            <div className="mua-camera-modal-header">
              <span><Camera size={16}/> Take Photo</span>
              <button className="mua-camera-close" onClick={closeCamera}><X size={18}/></button>
            </div>
            <div className="mua-camera-video-wrap">
              <video ref={videoRef} autoPlay playsInline className="mua-camera-video"/>
            </div>
            <div className="mua-camera-modal-footer">
              <button className="mua-camera-capture-btn" onClick={capturePhoto}>
                <Camera size={16}/> Capture Photo
              </button>
              <button className="mua-camera-cancel-btn" onClick={closeCamera}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <main className="mua-main">

        {/* ── Header ── */}
        <div className="mua-header">
          <div className="mua-header-left">
            <div className="mua-header-icon">
              <Sparkles size={22} />
            </div>
            <div>
              <h1>Makeup Assistance</h1>
              <p>Upload your photo, pick your event, and get AI-powered personalised recommendations.</p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
            {phase === 'done' && (
              <button className="mua-reset-btn" onClick={handleReset}>
                <RotateCcw size={14}/> New Analysis
              </button>
            )}
            <button className="mua-reset-btn" onClick={() => navigate('/home')}>
              <Home size={14}/> Home
            </button>
          </div>
        </div>

        {/* ══ IDLE / LOADING PHASE ══ */}
        {phase !== 'done' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem' }}>

            {/* Left col — upload */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="card" style={{ padding: '1.5rem' }}>
                <p className="mua-section-label">Step 1 · Upload Photo</p>

                {!imgSrc ? (
                  <div
                    className={`mua-upload-zone ${dragging ? 'drag-over' : ''}`}
                    onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
                  >
                    <input
                      type="file" accept="image/*" ref={fileInputRef}
                      onChange={onFileChange} tabIndex={-1}
                    />
                    <div className="mua-upload-icon"><Camera size={26}/></div>
                    <p className="mua-upload-title">Upload a clear front-face photo</p>
                    <p className="mua-upload-sub">PNG, JPG or WEBP · Good lighting recommended</p>
                    <div className="mua-upload-actions">
                      <label className="mua-upload-btn-label">
                        <Upload size={13}/> Choose Photo
                        <input type="file" accept="image/*" style={{ display: 'none' }} onChange={onFileChange}/>
                      </label>
                      <button type="button" className="mua-camera-btn" onClick={openCamera}>
                        <Video size={13}/> Take Photo
                      </button>
                    </div>
                    {cameraError && <p className="mua-camera-error">{cameraError}</p>}
                    <p className="mua-upload-sub" style={{ marginTop: '0.6rem' }}>or drag & drop here</p>
                  </div>
                ) : (
                  <div className="mua-preview-wrap">
                    <img src={imgSrc} alt="Uploaded face" />
                    <button className="mua-preview-change" onClick={() => fileInputRef.current?.click()}>
                      <ImageIcon size={12}/> Change
                    </button>
                    <div className="mua-preview-label">
                      <CheckCircle2 size={13}/> Photo ready for analysis
                    </div>
                    <input type="file" accept="image/*" ref={fileInputRef} onChange={onFileChange} style={{ display:'none' }}/>
                  </div>
                )}
              </div>
            </div>

            {/* Right col — event + analyse */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div className="card" style={{ padding: '1.5rem' }}>
                <p className="mua-section-label">Step 2 · Select Event Type</p>
                <div className="mua-event-grid">
                  {EVENT_TYPES.map(ev => (
                    <button
                      key={ev.id}
                      className={`mua-event-btn ${selectedEvent === ev.id ? 'active' : ''}`}
                      onClick={() => setSelectedEvent(ev.id)}
                      type="button"
                    >
                      <span className="mua-event-emoji">{ev.emoji}</span>
                      <span className="mua-event-label">{ev.label}</span>
                    </button>
                  ))}
                </div>

                {selectedEvent === 'other' && (
                  <input
                    className="mua-other-input"
                    placeholder="Describe your event (e.g. Graduation, Date Night…)"
                    value={otherText}
                    onChange={e => setOtherText(e.target.value)}
                  />
                )}
              </div>

              {/* Analyse button / loading */}
              <div className="card" style={{ padding: '1.5rem' }}>
                {phase === 'idle' ? (
                  <>
                    <p className="mua-section-label">Step 3 · Get Your Look</p>
                    <button
                      className="mua-analyze-btn"
                      onClick={handleAnalyze}
                      disabled={!canAnalyze}
                    >
                      <Wand2 size={18}/> Analyse My Look
                    </button>
                    {!canAnalyze && (
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', marginTop: '0.6rem', textAlign: 'center' }}>
                        {!imgSrc ? 'Upload a photo first' : 'Select an event type to continue'}
                      </p>
                    )}
                    {apiError && (
                      <p role="alert" aria-live="assertive" style={{
                        fontSize: '0.8rem', color: '#ef4444', marginTop: '0.6rem',
                        textAlign: 'center', padding: '0.5rem 0.75rem',
                        background: 'rgba(239,68,68,0.08)', borderRadius: '0.5rem',
                      }}>
                        {apiError}
                      </p>
                    )}
                  </>
                ) : (
                  <div className="mua-loading">
                    <div className="mua-loading-spinner"/>
                    <div>
                      <p className="mua-loading-title">Analysing your features…</p>
                      <p className="mua-loading-sub">Our AI is personalising your look</p>
                    </div>
                    <div className="mua-progress-bar-wrap">
                      <div className="mua-progress-bar-fill" style={{ width: `${progress}%` }}/>
                    </div>
                    <p className="mua-progress-step">{LOADING_STEPS[stepIdx]}</p>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>{progress}%</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══ RESULTS PHASE ══ */}
        {phase === 'done' && rec && (
          <div className="mua-results" ref={resultsRef}>

            {/* Event badge */}
            <div className="mua-event-badge">
              {EVENT_TYPES.find(e => e.id === selectedEvent)?.emoji || '🎨'}&nbsp;
              {eventLabel} Look — {rec.palette}
            </div>

            {/* Recommendations — 4 columns × 2 rows */}
            <p className="mua-section-label" style={{ marginBottom: '0.75rem' }}>Personalised Makeup Recommendations</p>
            <div className="mua-rec-grid mua-rec-grid--4col">
                  {Object.entries(rec).filter(([key]) => key !== 'palette' && !key.startsWith('_')).map(([key, val], i) => {
                    const meta = CARD_META[key];
                    if (!meta) return null;
                    if (!val || typeof val !== 'object' || !Array.isArray(val.shades)) return null;
                    return (
                      <div className="mua-rec-card" key={key} style={{ animationDelay: `${i * 0.07}s` }}>
                        <div className="mua-rec-card-header">
                          <div className="mua-rec-card-icon" style={{ background: meta.bg, color: meta.color }}>
                            {meta.icon}
                          </div>
                          <div>
                            <div className="mua-rec-card-title">{meta.label}</div>
                            <div className="mua-rec-card-category">{val.shade}</div>
                          </div>
                        </div>
                        <div className="mua-shade-row">
                          {val.shades.map((sh, si) => (
                            <div className="mua-shade-card" key={si}>
                              <div className="mua-shade-swatch" style={{ background: sh.color }}/>
                              <div className="mua-shade-card-body">
                                <span className="mua-shade-name">{sh.name}</span>
                                <span className="mua-shade-hex">{sh.color.toUpperCase()}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                        <p className="mua-rec-card-tip">{val.tip}</p>
                      </div>
                    );
                  })}
            </div>

            {/* Under the cards: Book Salon + Your Look at a Glance (full width) */}
            <div className="mua-under-cards">
              <button
                className="mua-salon-btn"
                onClick={() => navigate('/bookings?type=salon', { state: { type: 'salon', source: 'makeup' } })}
              >
                <Scissors size={16}/> Book Salon Appointment
              </button>

              <div className="card" style={{ padding: '1.25rem' }}>
                <p className="mua-section-label">Your Look at a Glance</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginTop: '0.25rem' }}>
                  {[
                    { label: 'Palette',  val: rec.palette },
                    { label: 'Eyes',     val: rec.eyes?.shade },
                    { label: 'Lips',     val: rec.lips?.shade },
                    { label: 'Blush',    val: rec.blush?.shade },
                    { label: 'Glow',     val: rec.highlighter?.shade },
                  ].filter(row => row.val).map(row => (
                    <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.77rem', color: 'var(--text-tertiary)', fontWeight: 600 }}>{row.label}</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-primary)', fontWeight: 600, textAlign: 'right', maxWidth: '62%' }}>{row.val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mua-divider"/>

            {/* ── Step-by-step guide ── */}
            <div className="card" style={{ padding: '1.5rem' }}>
              <button
                onClick={() => setShowSteps(s => !s)}
                style={{
                  display: 'flex', width: '100%', alignItems: 'center',
                  justifyContent: 'space-between', background: 'none',
                  border: 'none', cursor: 'pointer', padding: 0,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{
                    width: 32, height: 32, borderRadius: '0.6rem',
                    background: 'linear-gradient(135deg,#f9a8d4,#c084fc)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#fff',
                  }}><Sparkles size={15}/></span>
                  <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                    Step-by-Step Application Guide
                  </span>
                </div>
                <span style={{ color: 'var(--text-tertiary)' }}>
                  {showSteps ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
                </span>
              </button>

              {showSteps && (
                <div className="mua-steps-wrap" style={{ marginTop: '1.1rem' }}>
                  {steps.map((step, i) => (
                    <div className="mua-step" key={i} style={{ animationDelay: `${i * 0.06}s` }}>
                      <div className="mua-step-num">{i + 1}</div>
                      <div className="mua-step-body">
                        <p className="mua-step-title">{step.title}</p>
                        <p className="mua-step-desc">{step.desc}</p>
                        <span className="mua-step-tip">{step.tip}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Disclaimer */}
            <p style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', textAlign: 'center', marginTop: '1.5rem' }}>
              AI-generated recommendations — individual results vary. Always patch-test new products.
            </p>

            {/* ── Live Google Maps: nearby salons ─────────────────── */}
            <div className="card" style={{ padding: '1.25rem', marginTop: '1.25rem' }}>
              <NearbyProvidersMap
                searchType="salon"
                title="Nearby Salons & Beauty Studios"
                subtitle="Real-time results from Google Maps — book a professional for the look above."
                onBookProvider={(place) => navigate('/bookings?type=salon', {
                  state: {
                    type: 'salon',
                    source: 'makeup',
                    googlePlace: {
                      place_id: place.place_id,
                      name: place.name,
                      vicinity: place.vicinity,
                      lat: place._loc?.lat,
                      lng: place._loc?.lng,
                    },
                  },
                })}
              />
            </div>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
