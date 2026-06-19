import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Shirt, Upload, Home, RotateCcw, CheckCircle2,
  Camera, Wand2, ChevronDown, ChevronUp, ImageIcon,
  Sparkles, Star, ShoppingBag, Watch, Gem, Footprints,
  Layers, Palette, TrendingUp, BookOpen, Scissors, X, Video,
} from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import NearbyProvidersMap from '../components/NearbyProvidersMap';
import apiClient from '../api/client';
import { API_ENDPOINTS } from '../api/config';
import './FashionAssistance.css';

/* ════════════════════════════════════════════════════════════════════
   DATA
════════════════════════════════════════════════════════════════════ */

const EVENT_TYPES = [
  { id: 'formal',      label: 'Formal',           emoji: '🎓' },
  { id: 'casual',      label: 'Casual',            emoji: '👚' },
  { id: 'party',       label: 'Party',             emoji: '🎉' },
  { id: 'wedding',     label: 'Wedding',           emoji: '💍' },
  { id: 'office',      label: 'Office Wear',       emoji: '💼' },
  { id: 'street',      label: 'Street Style',      emoji: '🌆' },
  { id: 'dinner',      label: 'Dinner',            emoji: '🍷' },
  { id: 'traditional', label: 'Traditional',       emoji: '🦀' },
  { id: 'other',       label: 'Other',             emoji: '🎨' },
];

/* Body types detected by the simulated AI */
const BODY_TYPES = [
  {
    id: 'hourglass', label: 'Hourglass', emoji: '⏳',
    desc: 'Balanced bust and hips with a defined waist. Most styles suit this shape naturally.',
  },
  {
    id: 'pear', label: 'Pear Shape', emoji: '🍐',
    desc: 'Hips wider than shoulders. Emphasis on the upper body creates visual balance.',
  },
  {
    id: 'apple', label: 'Apple Shape', emoji: '🍎',
    desc: 'Fuller midsection with slimmer legs. Empire waists and A-line cuts are your friends.',
  },
  {
    id: 'rectangle', label: 'Rectangle', emoji: '📏',
    desc: 'Shoulders, waist, and hips are similar width. Adding curves through clothing creates dimension.',
  },
  {
    id: 'inverted', label: 'Inverted Triangle', emoji: '🔻',
    desc: 'Broader shoulders, narrower hips. Volume on lower half balances proportions beautifully.',
  },
  {
    id: 'petite', label: 'Petite', emoji: '🌸',
    desc: 'Shorter frame with fine proportions. Vertical lines and monochromatic outfits elongate the silhouette.',
  },
  {
    id: 'athletic', label: 'Athletic', emoji: '🏃',
    desc: 'Toned, muscular build with defined shoulders. Feminine details soften athletic lines beautifully.',
  },
  {
    id: 'plus', label: 'Plus / Curvy', emoji: '💗',
    desc: 'Full curves throughout. Well-fitting, structured pieces highlight your proportions confidently.',
  },
];

/* ── Fashion recommendations per event ── */
const FASHION_RECS = {
  formal: {
    palette: 'Classic Elegance',
    aesthetics: ['Sophisticated', 'Timeless', 'Polished', 'Understated Luxury'],
    aestheticColors: ['#1e3a5f','#2d6a4f','#6b2737','#3d2645'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Silk blouse', 'Structured fitted top', 'Cowl-neck top', 'Embellished camisole'],
      tip: 'Choose silk or satin fabrics in neutral tones. Avoid heavy patterns for formal settings.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Tailored wide-leg trousers', 'Pencil skirt', 'A-line midi skirt', 'Pleated palazzo'],
      tip: 'High-waisted cuts elongate the figure. Stick to solid colours or subtle textures.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Floor-length gown', 'Sheath dress', 'Wrap dress in crepe', 'Column dress'],
      tip: 'Floor-length or knee-length dresses signal formality. Choose structured fabrics.',
    },
    jackets: {
      title: 'Jackets & Cover-ups', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Tailored blazer', 'Structured jacket', 'Evening cape', 'Long-line coat'],
      tip: 'A well-fitted blazer elevates any formal outfit instantly. Single-breasted is most versatile.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Classic stiletto heels', 'Block-heel pumps', 'Strappy sandals', 'Pointed-toe flats'],
      tip: 'Neutral heels elongate the leg. Closed-toe court shoes are the safest formal choice.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Structured clutch', 'Minimalist tote', 'Envelope bag'],
      tip: 'Keep accessories minimal and intentional. One statement piece is enough.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Pearl earrings', 'Diamond studs', 'Tennis bracelet', 'Delicate necklace'],
      tip: 'Fine jewellery over costume pieces. Less is more in formal settings.',
    },
    colors: [
      { name: 'Midnight Navy', color: '#1a2456' },
      { name: 'Ivory White', color: '#FFFFF0' },
      { name: 'Charcoal', color: '#36454F' },
      { name: 'Champagne', color: '#F7E7CE' },
      { name: 'Bordeaux', color: '#7B1E3E' },
    ],
  },
  casual: {
    palette: 'Easy & Effortless',
    aesthetics: ['Minimalist', 'Clean Girl', 'Soft Casual', 'Everyday Chic'],
    aestheticColors: ['#374151','#059669','#db2777','#d97706'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Fitted tee', 'Linen shirt', 'Ribbed tank', 'Oversized knit'],
      tip: 'Tuck in your top or do a half-tuck to add definition effortlessly.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Straight-leg jeans', 'Cargo pants', 'Mini skirt', 'Linen trousers'],
      tip: 'Straight or wide-leg jeans are universally flattering for casual wear.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Sundress', 'Shirt dress', 'Slip dress over tee', 'Babydoll dress'],
      tip: 'Layer a shirt dress open over a plain tee for a relaxed, stylish look.',
    },
    jackets: {
      title: 'Outerwear', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Denim jacket', 'Bomber jacket', 'Oversized blazer', 'Zip-up hoodie'],
      tip: 'An oversized blazer over a simple outfit instantly upgrades the look.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['White trainers', 'Ballet flats', 'Platform sandals', 'Loafers'],
      tip: 'Clean white trainers are the most versatile casual shoe you can own.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Canvas tote', 'Crossbody bag', 'Bucket bag'],
      tip: 'A great bag pulls a casual outfit together. Opt for neutral tones.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Hoop earrings', 'Layered chains', 'Beaded bracelets', 'Stud earrings'],
      tip: 'Layer simple gold or silver pieces for a relaxed, effortless look.',
    },
    colors: [
      { name: 'White', color: '#FFFFFF' },
      { name: 'Beige', color: '#F5F5DC' },
      { name: 'Denim Blue', color: '#1560BD' },
      { name: 'Sage Green', color: '#87AE73' },
      { name: 'Terracotta', color: '#C05C35' },
    ],
  },
  party: {
    palette: 'Bold & Statement',
    aesthetics: ['Glam', 'Maximalist', 'Y2K Revival', 'Club Chic'],
    aestheticColors: ['#db2777','#7c3aed','#b45309','#0891b2'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Sequin crop top', 'Satin corset top', 'Metallic bralette', 'Ruched bodysuit'],
      tip: 'Sequins, satin, and metallics catch the light beautifully at parties.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Mini skirt', 'Leather-look trousers', 'Slit midi skirt', 'Sequin shorts'],
      tip: 'A mini skirt pairs with a toned-down top for perfectly balanced party dressing.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Bodycon mini', 'Sequin midi', 'Wrap satin dress', 'Cut-out dress'],
      tip: 'A bodycon or sequin dress needs minimal styling. Let the dress do the talking.',
    },
    jackets: {
      title: 'Outerwear', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Faux fur stole', 'Metallic blazer', 'Cropped leather jacket'],
      tip: 'A faux-fur stole or metallic jacket transforms any party look into a showstopper.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Strappy heeled sandals', 'Platform boots', 'Mule heels', 'Clear heels'],
      tip: 'Strappy heels or platform boots add height and drama to party outfits.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Embellished clutch', 'Mini chain bag', 'Metallic evening bag'],
      tip: 'Go bold with a statement bag. Embellishments and metallics work perfectly.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Chandelier earrings', 'Layered body chains', 'Statement ring', 'Rhinestone cuff'],
      tip: 'Go maximalist with jewellery at parties. Stack, layer, and shine.',
    },
    colors: [
      { name: 'Hot Pink', color: '#FF69B4' },
      { name: 'Electric Purple', color: '#8B00FF' },
      { name: 'Gold', color: '#D4AF37' },
      { name: 'Black', color: '#1C1C1C' },
      { name: 'Silver', color: '#C0C0C0' },
    ],
  },
  wedding: {
    palette: 'Romantic & Ethereal',
    aesthetics: ['Romantic', 'Soft Glam', 'Cottagecore Elegance', 'Modern Bride'],
    aestheticColors: ['#be185d','#b45309','#6d28d9','#0f766e'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Lace blouse', 'Embroidered corset', 'Floral chiffon top', 'Ruffle shoulder top'],
      tip: 'Delicate lace or embroidery adds a romantic, wedding-appropriate touch.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Tulle midi skirt', 'Flowy maxi skirt', 'Satin wide-leg trousers'],
      tip: 'Tulle or chiffon skirts create an ethereal, romantic look for wedding guests.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Floral midi dress', 'Satin slip gown', 'Off-shoulder dress', 'Lace maxi dress'],
      tip: 'Avoid white or ivory as a guest. Soft pastels and florals are most appropriate.',
    },
    jackets: {
      title: 'Cover-ups', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Sheer organza jacket', 'Lace bolero', 'Floral kimono', 'Embroidered shawl'],
      tip: 'A delicate lace bolero or organza jacket adds elegance without overshadowing.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Strappy kitten heels', 'Embellished sandals', 'Block-heel mules', 'Pearl-detail flats'],
      tip: 'Kitten heels offer elegance with comfort for long wedding celebrations.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Floral clutch', 'Satin evening bag', 'Wristlet bag'],
      tip: 'A small, dainty bag in satin or floral complements wedding guest attire.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Pearl drop earrings', 'Floral hairpin', 'Dainty necklace', 'Delicate bracelet'],
      tip: 'Pearls and floral accessories are timeless for weddings. Keep it romantic.',
    },
    colors: [
      { name: 'Blush Pink', color: '#FFB6C1' },
      { name: 'Dusty Rose', color: '#D8A0A0' },
      { name: 'Lavender', color: '#E6E6FA' },
      { name: 'Sage', color: '#87AE73' },
      { name: 'Powder Blue', color: '#B0E0E6' },
    ],
  },
  office: {
    palette: 'Power Dressing',
    aesthetics: ['Clean Professional', 'Quiet Luxury', 'Business Chic', 'Modern Corporate'],
    aestheticColors: ['#1e40af','#374151','#6b2737','#065f46'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Crisp white shirt', 'Fitted turtleneck', 'Silk blouse', 'Structured knit top'],
      tip: 'A well-ironed white shirt is the most powerful office wardrobe staple.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Tailored trousers', 'Midi pencil skirt', 'Wide-leg suit pants', 'A-line midi skirt'],
      tip: 'Tailored trousers in neutral tones are the cornerstone of office dressing.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Sheath dress', 'Wrap dress', 'Shirt dress', 'Midi shift dress'],
      tip: 'A knee-to-midi length sheath or wrap dress is office-appropriate and polished.',
    },
    jackets: {
      title: 'Jackets', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Structured blazer', 'Suit jacket', 'Long-line coat', 'Ponte blazer'],
      tip: 'A blazer is non-negotiable for a professional environment. Own at least two.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Court shoes', 'Block-heel pumps', 'Loafers', 'Pointed-toe flats'],
      tip: 'Court shoes or loafers in neutral leather tones complete a professional look.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Structured tote', 'Leather briefcase', 'Croc-effect handbag'],
      tip: 'Invest in a quality structured tote or leather bag for the office. Quality matters.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Stud earrings', 'Thin bangle', 'Simple watch', 'Delicate pendant'],
      tip: 'Keep jewellery subtle and refined. A good watch is the ultimate office accessory.',
    },
    colors: [
      { name: 'Navy Blue', color: '#003153' },
      { name: 'Charcoal', color: '#36454F' },
      { name: 'Camel', color: '#C19A6B' },
      { name: 'Ivory', color: '#FFFFF0' },
      { name: 'Dusty Pink', color: '#DCAE96' },
    ],
  },
  street: {
    palette: 'Urban Edge',
    aesthetics: ['Streetwear', 'Hypebeast', 'GRWM Casual', 'Urban Cool'],
    aestheticColors: ['#111827','#dc2626','#d97706','#0891b2'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Graphic tee', 'Cropped hoodie', 'Band tee', 'Mesh layering top'],
      tip: 'Tuck or knot a graphic tee for instant street-style points.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Baggy cargo pants', 'Distressed jeans', 'Joggers', 'Mini skirt with tights'],
      tip: 'Baggy cargo pants balanced with a fitted top is a go-to street formula.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['T-shirt dress', 'Slip dress over hoodie', 'Jersey mini dress'],
      tip: 'Layer a slip dress over a hoodie or long-sleeve for urban layering.',
    },
    jackets: {
      title: 'Outerwear', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Varsity jacket', 'Puffer jacket', 'Windbreaker', 'Oversized denim jacket'],
      tip: 'A puffer or varsity jacket is the defining piece of any street-style outfit.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Chunky sneakers', 'Nike Air Force 1s', 'Platform boots', 'Timberlands'],
      tip: 'Chunky sneakers or boots anchor any street-style outfit with attitude.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Mini backpack', 'Bum bag', 'Logo tote'],
      tip: 'A bum bag worn crossbody or a mini backpack is peak street-style utility.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Chunky chain necklace', 'Silver hoops', 'Ear cuff', 'Rings stacked'],
      tip: 'Stack rings and layer chunky chains for maximum street-style impact.',
    },
    colors: [
      { name: 'Black', color: '#1C1C1C' },
      { name: 'White', color: '#FFFFFF' },
      { name: 'Neon Yellow', color: '#CCFF00' },
      { name: 'Rust Orange', color: '#B7410E' },
      { name: 'Washed Grey', color: '#A9A9A9' },
    ],
  },
  dinner: {
    palette: 'Refined Evening',
    aesthetics: ['Smart Casual', 'Evening Chic', 'Effortless Glam', 'Date Night'],
    aestheticColors: ['#7c3aed','#be185d','#d97706','#1d4ed8'],
    tops: {
      title: 'Tops', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Silk cami', 'Off-shoulder top', 'Draped blouse', 'Embellished top'],
      tip: 'A silky cami or draped blouse elevates the dinner look with minimal effort.',
    },
    bottoms: {
      title: 'Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Satin midi skirt', 'Tailored trousers', 'Flared trousers', 'Slit skirt'],
      tip: 'A satin midi skirt with a tucked-in top is a failproof dinner look.',
    },
    dresses: {
      title: 'Dresses', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Wrap satin dress', 'Asymmetric hemline', 'Midi slip dress', 'Deep V gown'],
      tip: 'A midi or maxi wrap dress works for almost every dinner setting.',
    },
    jackets: {
      title: 'Cover-ups', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Fitted blazer', 'Sheer kimono', 'Velvet cropped jacket'],
      tip: 'A velvet or silk blazer transforms a dinner look into something special.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Strappy heels', 'Mule heels', 'Kitten-heel pumps', 'Embellished flats'],
      tip: 'Strappy or embellished heels add elegance without being overly formal.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Satin clutch', 'Mini chain bag', 'Embellished wristlet'],
      tip: 'A small, elegant bag keeps dinner dressing refined and functional.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Drop earrings', 'Thin layered necklaces', 'Cuff bracelet', 'Cocktail ring'],
      tip: 'A statement earring with a simple necklace is a foolproof dinner jewellery formula.',
    },
    colors: [
      { name: 'Midnight Black', color: '#1C1C1C' },
      { name: 'Deep Burgundy', color: '#7B1E3E' },
      { name: 'Emerald Green', color: '#046307' },
      { name: 'Rich Navy', color: '#003153' },
      { name: 'Blush Nude', color: '#E8C9A0' },
    ],
  },
  traditional: {
    palette: 'Cultural Heritage',
    aesthetics: ['Traditional Chic', 'Ethnic Fusion', 'Cultural Elegance', 'Heritage Luxe'],
    aestheticColors: ['#92400e','#7c3aed','#065f46','#be185d'],
    tops: {
      title: 'Tops / Kameez', icon: '👕', bg: '#EFF6FF', color: '#1D4ED8',
      items: ['Embroidered kurti', 'Silk kameez', 'Anarkali top', 'Printed choli'],
      tip: 'Intricate embroidery and rich fabrics like silk and brocade signal traditional luxury.',
    },
    bottoms: {
      title: 'Bottoms / Bottoms', icon: '👖', bg: '#F5F3FF', color: '#6D28D9',
      items: ['Palazzo pants', 'Churidar', 'Flared salwar', 'Sharara'],
      tip: 'Flared silhouettes such as sharara or palazzo complement most body types.',
    },
    dresses: {
      title: 'Full Outfits', icon: '👗', bg: '#FDF2F8', color: '#9D174D',
      items: ['Anarkali suit', 'Saree', 'Lehenga set', 'Gharara set'],
      tip: 'A well-draped saree or a fitted lehenga choli is timeless for traditional events.',
    },
    jackets: {
      title: 'Cover-ups', icon: '🧥', bg: '#ECFDF5', color: '#065F46',
      items: ['Dupatta / shawl', 'Embroidered jacket', 'Silk stole', 'Phulkari wrap'],
      tip: 'A richly embroidered dupatta draped elegantly elevates any traditional outfit.',
    },
    footwear: {
      title: 'Footwear', icon: '👡', bg: '#FFF7ED', color: '#9A3412',
      items: ['Embroidered juttis', 'Mojri / khussa', 'Block-heel sandals', 'Kolhapuri chappals'],
      tip: 'Embroidered juttis or kolhapuri sandals are the most authentic traditional pairing.',
    },
    accessories: {
      title: 'Accessories', icon: '👜', bg: '#FFFBEB', color: '#92400E',
      items: ['Potli bag', 'Embroidered clutch', 'Silk fabric bag'],
      tip: 'A potli bag in matching fabric or embroidery is the perfect traditional accessory.',
    },
    jewelry: {
      title: 'Jewellery', icon: '💎', bg: '#FDF4FF', color: '#6B21A8',
      items: ['Jhumka earrings', 'Maang tikka', 'Gold necklace set', 'Bangles/Choora', 'Nath (nose ring)'],
      tip: 'Layer traditional gold jewellery with culturally relevant pieces for authenticity.',
    },
    colors: [
      { name: 'Rich Red', color: '#8B0000' },
      { name: 'Royal Blue', color: '#002366' },
      { name: 'Emerald', color: '#046307' },
      { name: 'Turmeric Yellow', color: '#E5A900' },
      { name: 'Hot Pink', color: '#FF007F' },
    ],
  },
};

const DEFAULT_REC = FASHION_RECS.casual;

/* ── Body-type specific tips ── */
const BODY_TIPS = {
  hourglass: {
    dos: ['Belted waist styles', 'Wrap dresses and tops', 'Fitted silhouettes', 'High-waisted bottoms'],
    donts: ['Boxy, shapeless cuts', 'Overly baggy fits', 'Dropped waistlines'],
    fits: ['Fitted wrap styles', 'A-line skirts', 'Structured dresses', 'Pencil skirts'],
    colors: ['Any colour works', 'Bold colour-blocking', 'Prints that follow curves'],
  },
  pear: {
    dos: ['Bold tops and statement necklines', 'Bright colours on upper half', 'A-line and flared skirts', 'Wide-leg trousers'],
    donts: ['Tight-fitting trousers', 'Hip-hugging pencil skirts', 'Horizontal stripes on hips'],
    fits: ['A-line dresses', 'Empire waist', 'Off-shoulder tops', 'Bootcut jeans'],
    colors: ['Bright shades on top', 'Darker tones on bottom', 'Colour-blocking upward'],
  },
  apple: {
    dos: ['Empire waist dresses', 'V-necklines to elongate', 'Flowy A-line silhouettes', 'Wrap styles'],
    donts: ['High-waisted trousers at widest point', 'Clingy fabrics around midsection', 'Cropped tops'],
    fits: ['Wrap dresses', 'Shift dresses', 'Straight-leg trousers', 'Longline cardigans'],
    colors: ['Vertical stripes to elongate', 'Dark tones on midsection', 'Monochromatic dressing'],
  },
  rectangle: {
    dos: ['Peplum tops to create waist', 'Ruffles and volume at hips', 'Belted styles', 'Layering for dimension'],
    donts: ['Straight, boxy fits with no shape', 'Thin, clingy fabrics', 'Ultra-minimalist silhouettes'],
    fits: ['Fit and flare dresses', 'Peplum tops', 'Ruched styles', 'Layered outfits'],
    colors: ['Two-tone looks to create curves', 'Bold prints to add dimension', 'Contrasting top and bottom'],
  },
  inverted: {
    dos: ['Full skirts and wide-leg trousers', 'Volume below the waist', 'V-necklines to narrow shoulders', 'A-line cuts'],
    donts: ['Off-shoulder and boat necks', 'Padded shoulder jackets', 'Embellished tops', 'Cropped jackets'],
    fits: ['Flared midi skirts', 'Wide-leg palazzo', 'A-line dresses', 'Slip dresses'],
    colors: ['Bold and bright on lower half', 'Darker and minimal on top', 'Diagonal prints that draw eye downward'],
  },
  petite: {
    dos: ['Monochromatic outfits to elongate', 'Vertical stripes', 'High-waisted bottoms', 'Cropped styles'],
    donts: ['Oversized everything', 'Ankle straps that cut the leg', 'Heavily horizontal prints', 'Midi lengths that hit below the knee'],
    fits: ['Cropped jackets', 'Mini skirts', 'High-waist wide-leg trousers', 'Fitted midi dresses'],
    colors: ['Monochromatic head-to-toe', 'Tonal dressing', 'Vertical stripe prints'],
  },
  athletic: {
    dos: ['Feminine silhouettes to soften lines', 'Wrap styles to create curves', 'Ruffles and lace', 'Draped fabrics'],
    donts: ['Overly structured padded shoulders', 'Tight, body-hugging fits on top', 'Band collars on jackets'],
    fits: ['Wrap dresses', 'Flared trousers', 'Draped blouses', 'Maxi skirts'],
    colors: ['Softer pastels to feminise', 'Florals and prints', 'Gradient and ombre'],
  },
  plus: {
    dos: ['Well-fitted, not oversized', 'Structured fabrics that hold shape', 'V-necklines', 'Empire waist styles'],
    donts: ['Frumpy, baggy fits', 'Too-tight clingy fabrics', 'All-over bold horizontal stripes'],
    fits: ['A-line dresses', 'Wrap dresses', 'Straight-leg trousers', 'Long-line cardigans'],
    colors: ['Rich jewel tones', 'Monochromatic outfits', 'Diagonal and bias prints'],
  },
};

/* ── Loading animation steps ── */
const LOADING_STEPS = [
  'Scanning body proportions...',
  'Detecting body shape...',
  'Analysing height and balance...',
  'Evaluating styling compatibility...',
  'Matching event occasion...',
  'Generating outfit combinations...',
  'Selecting colour palette...',
  'Building accessory guide...',
  'Compiling fashion aesthetics...',
  'Finalising your personalised look...',
];

/* ── Card configuration ── */
const CARD_KEYS = ['tops','bottoms','dresses','jackets','footwear','accessories','jewelry'];

// Title/icon/colours per category — the LLM only returns {items, tip}, so the
// card heading + icon come from here.
const CATEGORY_META = {
  tops:        { title: 'Tops',                 icon: '👕', bg: '#EFF6FF', color: '#1D4ED8' },
  bottoms:     { title: 'Bottoms',              icon: '👖', bg: '#F5F3FF', color: '#6D28D9' },
  dresses:     { title: 'Dresses & Statement',  icon: '👗', bg: '#FDF2F8', color: '#9D174D' },
  jackets:     { title: 'Jackets & Outerwear',  icon: '🧥', bg: '#ECFDF5', color: '#065F46' },
  footwear:    { title: 'Footwear',             icon: '👞', bg: '#FFF7ED', color: '#9A3412' },
  accessories: { title: 'Accessories',          icon: '👜', bg: '#FFFBEB', color: '#92400E' },
  jewelry:     { title: 'Jewellery',            icon: '💎', bg: '#FDF4FF', color: '#6B21A8' },
};

/* ── Resolve a recommended colour to a real hex swatch ──
   The LLM may return colours as {name} (no hex) or {name, hex/color}.
   We honour an explicit hex, else map common fashion colour names. */
const FASHION_COLOR_HEX = {
  black:'#1C1C1C', white:'#FFFFFF', ivory:'#FFFFF0', cream:'#FFFDD0', beige:'#F5F5DC',
  charcoal:'#36454F', grey:'#808080', gray:'#808080', silver:'#C0C0C0',
  navy:'#1A2456', 'midnight navy':'#191970', midnight:'#191970', blue:'#1D4ED8',
  'royal blue':'#4169E1', teal:'#008080', denim:'#1560BD', cobalt:'#0047AB',
  burgundy:'#7B1E3E', bordeaux:'#7B1E3E', maroon:'#800000', wine:'#722F37',
  red:'#B22222', crimson:'#DC143C', rust:'#B7410E', terracotta:'#E2725B', coral:'#FF7F50',
  pink:'#F4A7A7', blush:'#DE99A0', rose:'#FF5C8A', mauve:'#9C687F', plum:'#8E4585',
  purple:'#6B21A8', lavender:'#C9A0DC', lilac:'#C8A2C8',
  green:'#3F704D', olive:'#808000', sage:'#9CAF88', emerald:'#50C878', forest:'#228B22', mint:'#98FF98',
  yellow:'#E4C441', gold:'#D4AF37', mustard:'#E1AD01', champagne:'#F7E7CE',
  orange:'#E07B39', peach:'#FFCBA4', apricot:'#FBCEB1',
  brown:'#8B5A2B', chocolate:'#5C3317', camel:'#C19A6B', tan:'#D2B48C', taupe:'#8B7E74',
  khaki:'#C3B091', sand:'#C2B280', nude:'#E3BC9A',
};
function resolveColorHex(c) {
  if (c && typeof c === 'object') {
    const hex = c.hex || c.color;
    if (typeof hex === 'string' && /^#?[0-9a-fA-F]{3,6}$/.test(hex.trim())) {
      return hex.trim().startsWith('#') ? hex.trim() : '#' + hex.trim();
    }
    const key = String(c.name || '').toLowerCase().trim();
    if (FASHION_COLOR_HEX[key]) return FASHION_COLOR_HEX[key];
    for (const k in FASHION_COLOR_HEX) { if (key.includes(k)) return FASHION_COLOR_HEX[k]; }
  } else if (typeof c === 'string') {
    const key = c.toLowerCase().trim();
    if (FASHION_COLOR_HEX[key]) return FASHION_COLOR_HEX[key];
    for (const k in FASHION_COLOR_HEX) { if (key.includes(k)) return FASHION_COLOR_HEX[k]; }
  }
  return '#9aa0aa';
}

/* ── Build styling guide steps ── */
function buildGuideSteps(eventLabel, rec, bodyType) {
  const bt = BODY_TIPS[bodyType?.id] || BODY_TIPS.rectangle;
  rec = rec || {};
  // Defensive accessors — the backend payload may omit some categories.
  const items = (cat) => (Array.isArray(cat?.items) ? cat.items.filter(Boolean) : []);
  const tipOf = (cat) => (cat && typeof cat.tip === 'string' ? cat.tip : '');
  const first = (cat, fallback) => items(cat)[0] || fallback;
  const join  = (cat, n, sep, fallback) => {
    const arr = items(cat).slice(0, n);
    return arr.length ? arr.join(sep) : fallback;
  };
  return [
    {
      title: 'Start with the right base',
      desc: 'Choose well-fitting underwear and shapewear if desired. A smooth base ensures every outfit sits correctly on the body.',
      tip: 'Great underwear is the most underrated styling secret.',
    },
    {
      title: 'Pick your hero piece',
      desc: 'Decide whether today is about a statement top, a show-stopping dress, or a bold bottom. Build the outfit around one standout piece.',
      tip: 'For '+eventLabel+': consider '+first(rec.dresses, 'a standout dress')+' as your hero.',
    },
    {
      title: 'Dress for your body shape',
      desc: bt.fits.slice(0,3).join(', ')+' are the most flattering cuts for your body type. Prioritise these silhouettes when selecting outfits.',
      tip: 'Fits that work best for you: '+bt.fits[0],
    },
    {
      title: 'Build your colour palette',
      desc: 'Select 2-3 colours from the recommended palette: '+(Array.isArray(rec.colors) ? rec.colors.map(c => (c && typeof c === 'object' ? c.name : String(c))).join(', ') : 'your skin-tone palette')+'. Stick to this palette for a cohesive look.',
      tip: 'Monochromatic dressing always looks intentional and polished.',
    },
    {
      title: 'Layer strategically',
      desc: 'Add depth with a jacket or cover-up. Options: '+join(rec.jackets, 2, ' or ', 'a tailored jacket or blazer')+'. Layering also allows for temperature adaptability.',
      tip: 'A '+first(rec.jackets, 'tailored jacket')+' is ideal for '+eventLabel,
    },
    {
      title: 'Select your footwear',
      desc: (tipOf(rec.footwear)+' Best options for '+eventLabel+': '+join(rec.footwear, 2, ', ', 'classic heels or flats')+'.').trim(),
      tip: 'Shoes set the tone of the entire outfit.',
    },
    {
      title: 'Choose your bag',
      desc: (tipOf(rec.accessories)+' Top picks: '+join(rec.accessories, 99, ', ', 'a structured clutch or tote')+'.').trim(),
      tip: 'A quality bag elevates even a simple outfit.',
    },
    {
      title: 'Add jewellery and accessories',
      desc: (tipOf(rec.jewelry)+' Suggested pieces: '+join(rec.jewelry, 3, ', ', 'delicate earrings and a necklace')+'.').trim(),
      tip: 'Layer pieces thoughtfully — not all at once.',
    },
    {
      title: 'Final check',
      desc: 'Stand in front of a full-length mirror. Check proportions, ensure nothing is pulling or bunching. Confidence is the final accessory.',
      tip: 'You are ready. Own your look.',
    },
  ];
}

/* Ensure every field the UI reads exists, with safe defaults, so a partial
   backend payload can never crash the render or the guide builder. */
function normalizeRec(raw) {
  const r = (raw && typeof raw === 'object') ? { ...raw } : {};
  const cat = (c) => ({
    items: Array.isArray(c?.items) ? c.items.filter(Boolean) : [],
    tip:   typeof c?.tip === 'string' ? c.tip : '',
  });
  // Outfit categories the cards + guide steps read.
  ['tops','bottoms','dresses','jackets','footwear','accessories','jewelry'].forEach(k => {
    r[k] = cat(r[k]);
  });
  // Colour + aesthetic arrays the render maps over.
  r.colors          = Array.isArray(r.colors) ? r.colors : [];
  r.aesthetics      = Array.isArray(r.aesthetics) ? r.aesthetics : [];
  r.aestheticColors = Array.isArray(r.aestheticColors) ? r.aestheticColors : [];
  return r;
}

/* ════════════════════════════════════════════════════════════════════
   Main Component
════════════════════════════════════════════════════════════════════ */
export default function FashionAssistance() {
  const navigate = useNavigate();

  /* Upload */
  const [imgSrc,   setImgSrc]   = useState(null);
  const [imgEl,    setImgEl]    = useState(null);
  const [imgFile,  setImgFile]  = useState(null);  // raw File for upload
  const [dragging, setDragging] = useState(false);
  const [apiError, setApiError] = useState('');

  /* Camera */
  const [cameraOpen,   setCameraOpen]   = useState(false);
  const [cameraStream, setCameraStream] = useState(null);
  const [cameraError,  setCameraError]  = useState('');
  const videoRef = useRef(null);

  /* Selections */
  const [selectedEvent, setSelectedEvent] = useState('');
  const [otherText,     setOtherText]     = useState('');
  // P1 — body measurements (preferred) + explicit body type pick (fallback)
  const [bust,   setBust]   = useState('');
  const [waist,  setWaist]  = useState('');
  const [hip,    setHip]    = useState('');
  const [bodyTypePick, setBodyTypePick] = useState('');
  const [season, setSeason] = useState('all-season');
  const [gender, setGender] = useState('female');   // drives male/female suggestions
  const [detectedBody,  setDetectedBody]  = useState(null);

  /* Analysis */
  const [phase,    setPhase]    = useState('idle');
  const [progress, setProgress] = useState(0);
  const [stepIdx,  setStepIdx]  = useState(0);

  /* Results */
  const [rec,          setRec]          = useState(null);
  const [showGuide,    setShowGuide]    = useState(false);
  const [showTips,     setShowTips]     = useState(true);

  /* Refs */
  const fileInputRef = useRef(null);
  const resultsRef   = useRef(null);

  /* ── Load image file ── */
  const loadFile = useCallback((file) => {
    if (!file || !file.type.startsWith('image/')) return;
    const url = URL.createObjectURL(file);
    const el  = new Image();
    el.onload = () => { setImgEl(el); setImgSrc(url); setImgFile(file); };
    el.src    = url;
  }, []);

  const onFileChange = e => loadFile(e.target.files[0]);
  const onDrop       = e => { e.preventDefault(); setDragging(false); loadFile(e.dataTransfer.files[0]); };
  const onDragOver   = e => { e.preventDefault(); setDragging(true); };
  const onDragLeave  = () => setDragging(false);

  /* ── Camera ──
     mediaDevices is undefined on HTTP origins on every modern mobile
     browser. Guard before touching it; surface a clear "use Choose Photo"
     fallback so the user is never stuck. */
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
    setCameraStream(null);
    setCameraOpen(false);
    setCameraError('');
  };

  const capturePhoto = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width  = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
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

  /* ── Client-side image size guard (P2) ── */
  const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

  /* ── Real backend analysis ── */
  const handleAnalyze = async () => {
    if (!imgSrc || !selectedEvent || !imgFile) return;
    if (imgFile.size > MAX_UPLOAD_BYTES) {
      setApiError('Image must be under 10 MB. Please pick a smaller file.');
      return;
    }
    setApiError('');
    setPhase('loading');
    setProgress(0);
    setStepIdx(0);

    const total = LOADING_STEPS.length;
    let p = 0;
    const tick = setInterval(() => {
      p += Math.random() * 7 + 2;
      if (p > 95) p = 95;
      setProgress(Math.round(p));
      setStepIdx(Math.min(total - 1, Math.floor((p / 100) * total)));
    }, 250);

    try {
      const formData = new FormData();
      formData.append('image', imgFile);
      formData.append('event_type', selectedEvent === 'other'
        ? (otherText.trim() || 'other')
        : selectedEvent);
      // P1 — send measurements + optional explicit body type pick.
      if (bust)         formData.append('bust',  bust);
      if (waist)        formData.append('waist', waist);
      if (hip)          formData.append('hip',   hip);
      if (bodyTypePick) formData.append('body_type', bodyTypePick);
      if (season)       formData.append('season', season);
      formData.append('gender', gender);

      const res = await apiClient.post(API_ENDPOINTS.FASHION.SUGGEST, formData, {
        headers: { 'Accept': 'application/json' },
        timeout: 180000,
      });

      const data = res.data?.data || res.data || {};

      // Body type from the backend (measurement-based or user pick).
      const serverBody = data.body_type || data.detected_body_type || null;
      const detected = serverBody
        ? (BODY_TYPES.find(b =>
            b.id?.toLowerCase() === String(serverBody).toLowerCase() ||
            b.label?.toLowerCase() === String(serverBody).toLowerCase()
          ) || BODY_TYPES[0])
        : BODY_TYPES[0];
      setDetectedBody(detected);

      // ── Normalize the payload so every field the UI reads always exists ──
      // The backend may omit categories / colour arrays; fill safe defaults
      // so neither the render nor buildGuideSteps can crash.
      const suggestions = normalizeRec(data.suggestions || data);
      const merged = {
        ...suggestions,
        _serverDetected: {
          body_type:  serverBody,
          skin_tone:  data.skin_tone || null,
        },
        _serverRaw: suggestions,
      };

      clearInterval(tick);
      setProgress(100);
      setStepIdx(total - 1);
      setRec(merged);
      setPhase('done');
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior:'smooth', block:'start' }), 120);
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
    setDetectedBody(null); setShowGuide(false); setApiError('');
    setProgress(0); setStepIdx(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  /* ── Cleanup camera on unmount ── */
  useEffect(() => () => { if (cameraStream) cameraStream.getTracks().forEach(t => t.stop()); }, [cameraStream]);

  const eventLabel = selectedEvent === 'other'
    ? (otherText.trim() || 'Custom Event')
    : EVENT_TYPES.find(e => e.id === selectedEvent)?.label || '';

  const canAnalyze = !!imgSrc && !!selectedEvent
    && (selectedEvent !== 'other' || otherText.trim().length > 0);

  const guideSteps = rec && detectedBody ? buildGuideSteps(eventLabel, rec, detectedBody) : [];
  const bodyTip    = detectedBody ? (BODY_TIPS[detectedBody.id] || BODY_TIPS.rectangle) : null;

  /* ─────────────────────────────────────────────────────────── render */
  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar />

      {/* Camera Modal */}
      {cameraOpen && (
        <div className="fa-camera-modal-overlay">
          <div className="fa-camera-modal">
            <div className="fa-camera-modal-header">
              <span><Camera size={16}/> Take Photo</span>
              <button className="fa-camera-close" onClick={closeCamera}><X size={18}/></button>
            </div>
            <div className="fa-camera-video-wrap">
              <video ref={videoRef} autoPlay playsInline className="fa-camera-video"/>
            </div>
            <div className="fa-camera-modal-footer">
              <button className="fa-camera-capture-btn" onClick={capturePhoto}>
                <Camera size={16}/> Capture Photo
              </button>
              <button className="fa-camera-cancel-btn" onClick={closeCamera}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <main className="fa-main">

        {/* ── Page header ── */}
        <div className="fa-header">
          <div className="fa-header-left">
            <div className="fa-header-icon"><Shirt size={24}/></div>
            <div>
              <h1>Fashion Assistance</h1>
              <p>Upload your photo, choose your occasion, and receive AI-powered personalised style recommendations.</p>
            </div>
          </div>
          <div style={{ display:'flex', gap:'0.6rem', flexWrap:'wrap', alignItems:'center' }}>
            {phase === 'done' && (
              <button className="fa-action-btn" onClick={handleReset}>
                <RotateCcw size={14}/> New Analysis
              </button>
            )}
            <button className="fa-action-btn" onClick={() => navigate('/home')}>
              <Home size={14}/> Home
            </button>
          </div>
        </div>

        {/* ══ INPUT PHASE ══ */}
        {phase !== 'done' && (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))', gap:'1.25rem' }}>

            {/* Left: Upload */}
            <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>
              <div className="card" style={{ padding:'1.5rem' }}>
                <p className="fa-section-label">Step 1 &mdash; Upload Full-Body Photo</p>

                {!imgSrc ? (
                  <div
                    className={`fa-upload-zone ${dragging ? 'drag-over' : ''}`}
                    onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
                  >
                    <input type="file" accept="image/*" ref={fileInputRef} onChange={onFileChange} tabIndex={-1}/>
                    <div className="fa-upload-icon"><Camera size={28}/></div>
                    <p className="fa-upload-title">Upload a clear full-body photo</p>
                    <p className="fa-upload-sub">Stand straight, full-body visible &bull; PNG, JPG or WEBP</p>
                    <div className="fa-upload-actions">
                      <label className="fa-upload-btn-label">
                        <Upload size={13}/> Choose Photo
                        <input type="file" accept="image/*" style={{ display:'none' }} onChange={onFileChange}/>
                      </label>
                      <button type="button" className="fa-camera-btn" onClick={openCamera}>
                        <Video size={13}/> Take Photo
                      </button>
                    </div>
                    {cameraError && <p className="fa-camera-error">{cameraError}</p>}
                    <p className="fa-upload-sub" style={{ marginTop:'0.6rem' }}>or drag &amp; drop</p>
                  </div>
                ) : (
                  <div className="fa-preview-wrap">
                    <img src={imgSrc} alt="Uploaded body" />
                    <button className="fa-preview-change" onClick={() => fileInputRef.current?.click()}>
                      <ImageIcon size={12}/> Change
                    </button>
                    <div className="fa-preview-label">
                      <CheckCircle2 size={13}/> Photo ready for analysis
                    </div>
                    <input type="file" accept="image/*" ref={fileInputRef} onChange={onFileChange} style={{ display:'none' }}/>
                  </div>
                )}
              </div>

              {/* Step 2 — occasion, now directly under the upload */}
              <div className="card" style={{ padding:'1.5rem' }}>
                <p className="fa-section-label">Step 2 &mdash; Select Occasion</p>
                <div className="fa-event-grid">
                  {EVENT_TYPES.map(ev => (
                    <button
                      key={ev.id}
                      className={`fa-event-btn ${selectedEvent === ev.id ? 'active' : ''}`}
                      onClick={() => setSelectedEvent(ev.id)}
                      type="button"
                    >
                      <span className="fa-event-emoji">{ev.emoji}</span>
                      <span className="fa-event-label">{ev.label}</span>
                    </button>
                  ))}
                </div>
                {selectedEvent === 'other' && (
                  <input
                    className="fa-other-input"
                    placeholder="Describe your occasion (e.g. Graduation, Picnic, Gala...)"
                    value={otherText}
                    onChange={e => setOtherText(e.target.value)}
                  />
                )}
              </div>
            </div>

            {/* Right: Gender + Measurements + Analyze */}
            <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>

              {/* Gender — drives male vs female recommendations */}
              <div className="card" style={{ padding:'1.25rem' }}>
                <p className="fa-section-label">Step 2 · Gender</p>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginBottom: '0.7rem' }}>
                  Recommendations are tailored to your selection.
                </p>
                <div style={{ display: 'flex', gap: '0.6rem' }}>
                  {[{ id: 'female', label: 'Female' }, { id: 'male', label: 'Male' }].map(g => (
                    <button
                      key={g.id}
                      type="button"
                      onClick={() => setGender(g.id)}
                      className={`fa-gender-btn ${gender === g.id ? 'selected' : ''}`}
                    >
                      {g.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* P1 — Measurement inputs (optional but preferred) ── */}
              <div className="card" style={{ padding:'1.25rem' }}>
                <p className="fa-section-label">Step 2.5 · Your Measurements (recommended)</p>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginBottom: '0.85rem' }}>
                  ✨ For the most accurate, personalised results, add your bust/waist/hip
                  in cm — this detects all body shapes (incl. Hourglass &amp; Apple) that a
                  photo alone can't. Or pick a body type below to skip.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                  <input
                    className="fa-other-input" type="number" min="40" max="200" inputMode="numeric"
                    placeholder="Bust (cm)" value={bust}
                    onChange={(e) => setBust(e.target.value)}
                    aria-label="Bust measurement in centimeters"
                  />
                  <input
                    className="fa-other-input" type="number" min="40" max="200" inputMode="numeric"
                    placeholder="Waist (cm)" value={waist}
                    onChange={(e) => setWaist(e.target.value)}
                    aria-label="Waist measurement in centimeters"
                  />
                  <input
                    className="fa-other-input" type="number" min="40" max="200" inputMode="numeric"
                    placeholder="Hip (cm)" value={hip}
                    onChange={(e) => setHip(e.target.value)}
                    aria-label="Hip measurement in centimeters"
                  />
                </div>
                <div style={{ marginTop: '0.75rem' }}>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>
                    Or pick a body type
                  </label>
                  <select
                    className="fa-other-input"
                    value={bodyTypePick}
                    onChange={(e) => setBodyTypePick(e.target.value)}
                    style={{ marginTop: '0.3rem' }}
                  >
                    <option value="">— Let AI decide from measurements —</option>
                    <option value="Hourglass">Hourglass</option>
                    <option value="Pear">Pear</option>
                    <option value="Apple">Apple</option>
                    <option value="Rectangle">Rectangle</option>
                    <option value="Inverted Triangle">Inverted Triangle</option>
                  </select>
                </div>
                <div style={{ marginTop: '0.75rem' }}>
                  <label style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>
                    Season
                  </label>
                  <select
                    className="fa-other-input"
                    value={season}
                    onChange={(e) => setSeason(e.target.value)}
                    style={{ marginTop: '0.3rem' }}
                  >
                    <option value="all-season">All-season</option>
                    <option value="spring">Spring</option>
                    <option value="summer">Summer</option>
                    <option value="autumn">Autumn</option>
                    <option value="winter">Winter</option>
                  </select>
                </div>
              </div>

              {/* Analyze button / loading */}
              <div className="card" style={{ padding:'1.5rem' }}>
                {phase === 'idle' ? (
                  <>
                    <p className="fa-section-label">Step 3 &mdash; Get Your Style</p>
                    <button
                      className="fa-analyze-btn"
                      onClick={handleAnalyze}
                      disabled={!canAnalyze}
                    >
                      <Wand2 size={18}/> Analyse My Style
                    </button>
                    {!canAnalyze && (
                      <p style={{ fontSize:'0.75rem', color:'var(--text-tertiary)', marginTop:'0.6rem', textAlign:'center' }}>
                        {!imgSrc ? 'Upload a photo first' : 'Select an occasion to continue'}
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
                  <div className="fa-loading">
                    <div className="fa-loading-spinner"/>
                    <div>
                      <p className="fa-loading-title">Analysing your style profile...</p>
                      <p className="fa-loading-sub">AI is detecting body shape and building your look</p>
                    </div>
                    <div className="fa-progress-wrap">
                      <div className="fa-progress-fill" style={{ width:`${progress}%` }}/>
                    </div>
                    <p className="fa-progress-step">{LOADING_STEPS[stepIdx]}</p>
                    <span style={{ fontSize:'0.78rem', color:'var(--text-tertiary)' }}>{progress}%</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══ RESULTS PHASE ══ */}
        {phase === 'done' && rec && detectedBody && (
          <div className="fa-results" ref={resultsRef}>

            {/* Event + palette badge */}
            <div className="fa-event-badge">
              {EVENT_TYPES.find(e => e.id === selectedEvent)?.emoji || '🎨'}&nbsp;
              {eventLabel} &mdash; {rec.palette}
            </div>

            {/* Body type card */}
            <div className="fa-body-card">
              <div className="fa-body-card-icon">{detectedBody.emoji}</div>
              <div style={{ flex:1 }}>
                <p className="fa-body-card-type">AI Detected Body Shape</p>
                <p className="fa-body-card-name">{detectedBody.label}</p>
                <p className="fa-body-card-desc">{detectedBody.desc}</p>
              </div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:'0.5rem', alignSelf:'center' }}>
                {(Array.isArray(rec.aesthetics) ? rec.aesthetics : []).map((a,i) => {
                  // Per-event accent color, passed through a CSS variable so
                  // the white-pill style in .fa-aesthetic-tag (scoped under
                  // .fa-body-card) can use it for the dot + text without
                  // being overridden by inline background/border colors —
                  // which on the purple gradient were unreadable.
                  const chipColor = (rec.aestheticColors && rec.aestheticColors[i]) || '#6366f1';
                  return (
                    <span
                      key={i}
                      className="fa-aesthetic-tag"
                      style={{ '--chip-color': chipColor }}
                    >
                      <span className="fa-aesthetic-dot" aria-hidden="true"/>
                      {a}
                    </span>
                  );
                })}
              </div>
            </div>

            {/* ── Main two-column grid ── */}
            <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(300px,1fr))', gap:'1.25rem', marginBottom:'1.5rem' }}>

              {/* Left: recommendations */}
              <div>
                <p className="fa-section-label" style={{ marginBottom:'0.75rem' }}>
                  Personalised Fashion Recommendations
                </p>
                <div className="fa-rec-grid">
                  {CARD_KEYS.map((key, i) => {
                    const item = rec[key];
                    const meta = CATEGORY_META[key] || { title: key, icon: '✦', bg: '#eef2ff', color: '#4f46e5' };
                    // Skip categories the LLM left empty (e.g. dresses for men).
                    if (!item || typeof item !== 'object'
                        || !Array.isArray(item.items) || item.items.length === 0) return null;
                    return (
                      <div
                        className="fa-rec-card"
                        key={key}
                        style={{ animationDelay:`${i * 0.07}s`, '--fa-accent':`linear-gradient(90deg,${rec.aestheticColors[0]||'#6366f1'},${rec.aestheticColors[1]||'#a855f7'})` }}
                      >
                        <div className="fa-rec-card-head">
                          <div
                            className="fa-rec-card-ico"
                            style={{ background: meta.bg, color: meta.color }}
                          >
                            {meta.icon}
                          </div>
                          <div>
                            <div className="fa-rec-card-title">{meta.title}</div>
                            <div className="fa-rec-card-sub">{eventLabel}</div>
                          </div>
                        </div>
                        <div className="fa-chip-row">
                          {item.items.map((it, si) => (
                            <span className="fa-chip" key={si}>{it}</span>
                          ))}
                        </div>
                        <p className="fa-rec-card-tip">{item.tip}</p>
                      </div>
                    );
                  })}
                </div>

              </div>

              {/* Right: preview + glance */}
              <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>

                {/* Book Salon Appointment (AR outfit preview removed) */}
                <button
                  className="fa-salon-btn"
                  onClick={() => navigate('/bookings?type=salon', { state: { type: 'salon', source: 'fashion' } })}
                >
                  <Scissors size={16}/> Book Salon Appointment
                </button>

                {/* Quick glance */}
                <div className="card" style={{ padding:'1.2rem' }}>
                  <p className="fa-section-label">Your Style at a Glance</p>
                  <div style={{ marginTop:'0.3rem' }}>
                    {[
                      { key:'Palette',     val: rec.palette },
                      { key:'Top Pick',    val: rec.tops?.items?.[0] },
                      { key:'Bottom Pick', val: rec.bottoms?.items?.[0] },
                      { key:'Footwear',    val: rec.footwear?.items?.[0] },
                      { key:'Jewellery',   val: rec.jewelry?.items?.[0] },
                      { key:'Aesthetic',   val: Array.isArray(rec.aesthetics) ? rec.aesthetics.slice(0,2).join(' / ') : null },
                    ].filter(r => r.val).map(row => (
                      <div className="fa-glance-row" key={row.key}>
                        <span className="fa-glance-key">{row.key}</span>
                        <span className="fa-glance-val">{row.val}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Colour palette — now in the right column under the glance */}
                <div className="card" style={{ padding:'1.2rem' }}>
                  <p className="fa-section-label">Recommended Colour Palette</p>
                  <div className="fa-palette-grid">
                    {(Array.isArray(rec.colors) ? rec.colors : []).map((c,i) => {
                      const name  = c && typeof c === 'object' ? (c.name  || 'Colour') : String(c);
                      const color = resolveColorHex(c);
                      return (
                        <div className="fa-palette-card" key={i}>
                          <div className="fa-palette-swatch" style={{ background: color }}/>
                          <div className="fa-palette-card-body">
                            <span className="fa-palette-name">{name}</span>
                            <span className="fa-palette-hex">{String(color).toUpperCase()}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="fa-divider"/>

            {/* ── Body shape tips ── */}
            {bodyTip && (
              <div className="card" style={{ padding:'1.5rem', marginBottom:'1.25rem' }}>
                <button className="fa-collapse-btn" onClick={() => setShowTips(v => !v)}>
                  <div className="fa-collapse-btn-left">
                    <div className="fa-collapse-icon" style={{ background:'linear-gradient(135deg,#6366f1,#a855f7)' }}>
                      <TrendingUp size={15}/>
                    </div>
                    <span className="fa-collapse-title">
                      Body Shape Styling Guide &mdash; {detectedBody.label}
                    </span>
                  </div>
                  <span style={{ color:'var(--text-tertiary)' }}>
                    {showTips ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
                  </span>
                </button>

                {showTips && (
                  <div className="fa-tips-grid" style={{ marginTop:'1.1rem' }}>
                    <div className="fa-tips-box do">
                      <p className="fa-tips-box-title"><span>&#10003;</span> What to Wear</p>
                      <ul>{bodyTip.dos.map((d,i) => <li key={i}>{d}</li>)}</ul>
                    </div>
                    <div className="fa-tips-box dont">
                      <p className="fa-tips-box-title"><span>&#10005;</span> What to Avoid</p>
                      <ul>{bodyTip.donts.map((d,i) => <li key={i}>{d}</li>)}</ul>
                    </div>
                    <div className="fa-tips-box fit">
                      <p className="fa-tips-box-title"><Layers size={12}/> Best Fits & Silhouettes</p>
                      <ul>{bodyTip.fits.map((d,i) => <li key={i}>{d}</li>)}</ul>
                    </div>
                    <div className="fa-tips-box color">
                      <p className="fa-tips-box-title"><Palette size={12}/> Colour Strategy</p>
                      <ul>{bodyTip.colors.map((d,i) => <li key={i}>{d}</li>)}</ul>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── Step-by-step styling guide ── */}
            <div className="card" style={{ padding:'1.5rem' }}>
              <button className="fa-collapse-btn" onClick={() => setShowGuide(v => !v)}>
                <div className="fa-collapse-btn-left">
                  <div className="fa-collapse-icon" style={{ background:'linear-gradient(135deg,#4f46e5,#ec4899)' }}>
                    <BookOpen size={15}/>
                  </div>
                  <span className="fa-collapse-title">Step-by-Step Styling Guide</span>
                </div>
                <span style={{ color:'var(--text-tertiary)' }}>
                  {showGuide ? <ChevronUp size={18}/> : <ChevronDown size={18}/>}
                </span>
              </button>

              {showGuide && (
                <div className="fa-guide-steps" style={{ marginTop:'1.1rem' }}>
                  {guideSteps.map((step, i) => (
                    <div className="fa-guide-step" key={i} style={{ animationDelay:`${i*0.06}s` }}>
                      <div className="fa-guide-num">{i + 1}</div>
                      <div>
                        <p className="fa-guide-title">{step.title}</p>
                        <p className="fa-guide-desc">{step.desc}</p>
                        <span className="fa-guide-tip">{step.tip}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <p style={{ fontSize:'0.75rem', color:'var(--text-tertiary)', textAlign:'center', marginTop:'1.5rem' }}>
              AI-generated style guidance &mdash; recommendations are personalised suggestions. Individual results may vary.
            </p>

            {/* ── Live Google Maps: nearby salons / studios ─────────── */}
            <div className="card" style={{ padding: '1.25rem', marginTop: '1.25rem' }}>
              <NearbyProvidersMap
                searchType="salon"
                title="Nearby Salons & Style Studios"
                subtitle="Real-time results from Google Maps — get this look done by a professional."
                onBookProvider={(place) => navigate('/bookings?type=salon', {
                  state: {
                    type: 'salon',
                    source: 'fashion',
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
