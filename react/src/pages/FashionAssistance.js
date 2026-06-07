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
    id: 'inverted', label: 'Inverted Triangle', emoji: '🔻D0',
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

/* ── Canvas outfit overlay ── */
function drawOutfitOverlay(canvas, img, rec, bodyType) {
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;
  ctx.drawImage(img, 0, 0, W, H);

  function hexToRgba(hex, a) {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    return 'rgba('+r+','+g+','+b+','+a+')';
  }

  const c1 = rec.colors[0]?.color || '#6366f1';
  const c2 = rec.colors[1]?.color || '#a855f7';
  const c3 = rec.colors[2]?.color || '#ec4899';

  // Clothing silhouette overlay — torso
  const cx = W * 0.5;
  const shoulderY = H * 0.22;
  const waistY    = H * 0.48;
  const hemY      = H * 0.78;
  const shoulderW = W * 0.38;
  const waistW    = W * 0.28;
  const hemW      = W * 0.36;

  // Top/blouse gradient
  const topGrd = ctx.createLinearGradient(cx - shoulderW, shoulderY, cx + shoulderW, waistY);
  topGrd.addColorStop(0, hexToRgba(c1, 0.45));
  topGrd.addColorStop(1, hexToRgba(c2, 0.4));
  ctx.save();
  ctx.globalAlpha = 0.7;
  ctx.fillStyle = topGrd;
  ctx.beginPath();
  ctx.moveTo(cx - shoulderW, shoulderY);
  ctx.lineTo(cx + shoulderW, shoulderY);
  ctx.lineTo(cx + waistW,    waistY);
  ctx.lineTo(cx - waistW,    waistY);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Skirt / bottom
  const botGrd = ctx.createLinearGradient(cx - waistW, waistY, cx + hemW, hemY);
  botGrd.addColorStop(0, hexToRgba(c2, 0.4));
  botGrd.addColorStop(1, hexToRgba(c3, 0.35));
  ctx.save();
  ctx.globalAlpha = 0.65;
  ctx.fillStyle = botGrd;
  ctx.beginPath();
  ctx.moveTo(cx - waistW, waistY);
  ctx.lineTo(cx + waistW, waistY);
  ctx.lineTo(cx + hemW,   hemY);
  ctx.lineTo(cx - hemW,   hemY);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  // Shimmer accent lines
  ctx.save();
  ctx.globalAlpha = 0.18;
  ctx.strokeStyle = '#fff';
  ctx.lineWidth = 1.5;
  for (let i = 0; i < 5; i++) {
    const x = cx - shoulderW + (shoulderW * 2 * i) / 4;
    ctx.beginPath();
    ctx.moveTo(x, shoulderY);
    ctx.lineTo(x - 5, waistY);
    ctx.stroke();
  }
  ctx.restore();

  // Colour palette swatches at bottom
  const swatchW = 24; const swatchH = 18; const swatchGap = 6;
  const totalSwatch = rec.colors.length * (swatchW + swatchGap) - swatchGap;
  let sx = cx - totalSwatch / 2;
  rec.colors.forEach(col => {
    ctx.save();
    ctx.fillStyle = col.color;
    ctx.beginPath();
    ctx.roundRect(sx, H - 36, swatchW, swatchH, 4);
    ctx.fill();
    ctx.restore();
    sx += swatchW + swatchGap;
  });

  // Footer label
  ctx.save();
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(0, H - 52, W, 52);
  ctx.restore();
  ctx.save();
  ctx.fillStyle = '#fff';
  ctx.font = 'bold '+Math.max(10,W*0.03)+'px Inter,sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('✨ AI Outfit Preview  –  '+rec.palette, cx, H - 42);
  ctx.restore();
}

/* ── Build styling guide steps ── */
function buildGuideSteps(eventLabel, rec, bodyType) {
  const bt = BODY_TIPS[bodyType?.id] || BODY_TIPS.rectangle;
  return [
    {
      title: 'Start with the right base',
      desc: 'Choose well-fitting underwear and shapewear if desired. A smooth base ensures every outfit sits correctly on the body.',
      tip: 'Great underwear is the most underrated styling secret.',
    },
    {
      title: 'Pick your hero piece',
      desc: 'Decide whether today is about a statement top, a show-stopping dress, or a bold bottom. Build the outfit around one standout piece.',
      tip: 'For '+eventLabel+': consider '+rec.dresses.items[0]+' as your hero.',
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
      desc: 'Add depth with a jacket or cover-up. Options: '+rec.jackets.items.slice(0,2).join(' or ')+'. Layering also allows for temperature adaptability.',
      tip: 'A '+rec.jackets.items[0]+' is ideal for '+eventLabel,
    },
    {
      title: 'Select your footwear',
      desc: rec.footwear.tip+' Best options for '+eventLabel+': '+rec.footwear.items.slice(0,2).join(', ')+'.',
      tip: 'Shoes set the tone of the entire outfit.',
    },
    {
      title: 'Choose your bag',
      desc: rec.accessories.tip+' Top picks: '+rec.accessories.items.join(', ')+'.',
      tip: 'A quality bag elevates even a simple outfit.',
    },
    {
      title: 'Add jewellery and accessories',
      desc: rec.jewelry.tip+' Suggested pieces: '+rec.jewelry.items.slice(0,3).join(', ')+'.',
      tip: 'Layer pieces thoughtfully — not all at once.',
    },
    {
      title: 'Final check',
      desc: 'Stand in front of a full-length mirror. Check proportions, ensure nothing is pulling or bunching. Confidence is the final accessory.',
      tip: 'You are ready. Own your look.',
    },
  ];
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
  const [detectedBody,  setDetectedBody]  = useState(null);

  /* Analysis */
  const [phase,    setPhase]    = useState('idle');
  const [progress, setProgress] = useState(0);
  const [stepIdx,  setStepIdx]  = useState(0);

  /* Results */
  const [rec,          setRec]          = useState(null);
  const [showGuide,    setShowGuide]    = useState(false);
  const [showTips,     setShowTips]     = useState(true);
  const [showPreview,  setShowPreview]  = useState(true);

  /* Refs */
  const fileInputRef = useRef(null);
  const canvasRef    = useRef(null);
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

      // ── P1 — backend now returns the exact frontend schema ──
      // No defensive merge needed; trust the validated payload.
      const suggestions = data.suggestions || data;
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

  /* ── Draw canvas overlay when results ready ── */
  useEffect(() => {
    if (phase !== 'done' || !rec || !imgEl || !canvasRef.current || !showPreview) return;
    const canvas = canvasRef.current;
    const MAX = 660;
    const ratio = Math.min(MAX / imgEl.width, MAX / imgEl.height, 1);
    canvas.width  = imgEl.width  * ratio;
    canvas.height = imgEl.height * ratio;
    drawOutfitOverlay(canvas, imgEl, rec, detectedBody);
  }, [phase, rec, imgEl, showPreview, detectedBody]);

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
            </div>

            {/* Right: Event + Analyze */}
            <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>
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

              {/* P1 — Measurement inputs (optional but preferred) ── */}
              <div className="card" style={{ padding:'1.25rem' }}>
                <p className="fa-section-label">Step 2.5 · Your Measurements (optional)</p>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)', marginBottom: '0.85rem' }}>
                  Add cm measurements for the most accurate body-type detection,
                  OR pick a body type below if you'd rather skip.
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
                    if (!item || typeof item !== 'object' || !Array.isArray(item.items)) return null;
                    return (
                      <div
                        className="fa-rec-card"
                        key={key}
                        style={{ animationDelay:`${i * 0.07}s`, '--fa-accent':`linear-gradient(90deg,${rec.aestheticColors[0]||'#6366f1'},${rec.aestheticColors[1]||'#a855f7'})` }}
                      >
                        <div className="fa-rec-card-head">
                          <div
                            className="fa-rec-card-ico"
                            style={{ background: item.bg, color: item.color }}
                          >
                            {item.icon}
                          </div>
                          <div>
                            <div className="fa-rec-card-title">{item.title}</div>
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

                {/* Colour palette — modern aesthetic cards */}
                <div className="card" style={{ padding:'1.15rem', marginTop:'1rem' }}>
                  <p className="fa-section-label">Recommended Colour Palette</p>
                  <div className="fa-palette-grid">
                    {(Array.isArray(rec.colors) ? rec.colors : []).map((c,i) => {
                      // Defensive: backend may return strings, objects, or odd shapes
                      const name  = c && typeof c === 'object' ? (c.name  || 'Colour') : String(c);
                      const color = c && typeof c === 'object' ? (c.color || '#888')   : '#888';
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

              {/* Right: preview + glance */}
              <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>

                {/* Virtual outfit preview */}
                <div className="fa-preview-section">
                  <div className="fa-preview-header">
                    <span className="fa-preview-title">
                      <Wand2 size={15}/> Virtual Outfit Preview
                    </span>
                    <div style={{ display:'flex', alignItems:'center', gap:'0.7rem' }}>
                      <button className="fa-toggle-preview" onClick={() => setShowPreview(v => !v)}>
                        {showPreview ? 'Hide' : 'Show'}
                      </button>
                    </div>
                  </div>
                  {showPreview && (
                    <div className="fa-preview-canvas-wrap">
                      <canvas ref={canvasRef}/>
                    </div>
                  )}
                  <div className="fa-preview-header" style={{ borderTop:'1px solid var(--border-color)', borderBottom:'none', justifyContent:'center' }}>
                    <button
                      className="fa-salon-btn"
                      onClick={() => navigate('/bookings?type=salon', { state: { type: 'salon', source: 'fashion' } })}
                    >
                      <Scissors size={16}/> Book Salon Appointment
                    </button>
                  </div>
                </div>

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
