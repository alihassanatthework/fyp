export default function Footer() {
  return (
    <footer className="py-4 px-6 border-t border-gray-100 border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-400">
      <span>© {new Date().getFullYear()} <strong className="text-gray-300">ME</strong> · AI-Powered Skin, Scalp, Makeup & Fashion Assistant</span>
      <div className="flex gap-4">
        <button
          onClick={() => alert('ME is an AI-powered beauty assistant for skin, scalp, makeup, and fashion analysis.\n\nBuilt by Team:\n• Huda Masood\n• Ali Hassan\n• Aqsa Mustafa\n• Sibgha Shezadi')}
          className="hover:text-white transition"
        >
          About Project
        </button>
        <a href="mailto:contact@meapp.placeholder.com" className="hover:text-white transition">
          Contact / Support
        </a>
      </div>
    </footer>
  );
}