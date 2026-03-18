import { useNavigate } from 'react-router-dom';
import { Smile, Scissors, FileText, Calendar, Bell, Palette, Sparkles, Grid, ArrowRight } from 'lucide-react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const notifications = [
  { color: 'bg-blue-500', text: 'Daily treatment reminder for your night routine.' },
  { color: 'bg-amber-400', text: 'Follow-up check recommended after your last scalp analysis.' },
  { color: 'bg-gray-400', text: 'New personalized recommendation available in your plan.' },
];

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title={null} subtitle={null} />

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-8">
        {/* Page header */}
        <div className="mb-7">
          <h1 className="font-display text-2xl font-bold text-gray-900 text-white">
            AI-Powered Skin, Scalp, Makeup &amp; Fashion Assistant
          </h1>
          <p className="text-sm text-gray-400 text-gray-500 mt-0.5">Welcome</p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Main column */}
          <div className="xl:col-span-2 space-y-5">

            {/* Quick Actions — top to bottom, prominent */}
            <section>
              <p className="text-sm font-semibold text-gray-500 text-gray-400 mb-3">Quick actions</p>
              <div className="flex flex-col gap-4">
                {[
                  {
                    icon: <Smile size={28} className="text-blue-500"/>,
                    title: 'Skin Analysis',
                    desc: 'Upload a face image for AI-based skin detection. Get instant insights on skin conditions, texture, and personalized care.',
                    btn: 'Analyze Skin',
                    to: '/analysis',
                    accent: 'border-blue-500',
                    bg: 'bg-blue-50 bg-blue-900/10',
                    btnClass: 'bg-blue-500 hover:bg-blue-600 text-white',
                  },
                  {
                    icon: <Scissors size={28} className="text-indigo-500"/>,
                    title: 'Scalp Analysis',
                    desc: 'Upload a scalp image to detect dandruff, dryness & more. Receive targeted scalp health recommendations.',
                    btn: 'Analyze Scalp',
                    to: '/analysis',
                    accent: 'border-indigo-500',
                    bg: 'bg-indigo-50 bg-indigo-900/10',
                    btnClass: 'bg-indigo-500 hover:bg-indigo-600 text-white',
                  },
                  {
                    icon: <FileText size={28} className="text-violet-500"/>,
                    title: 'Diagnosis Reports',
                    desc: 'View your history and AI-generated diagnosis summaries. Track your skin and scalp health over time.',
                    btn: 'My Reports',
                    to: '/analysis-history',
                    accent: 'border-violet-500',
                    bg: 'bg-violet-50 bg-violet-900/10',
                    btnClass: 'bg-violet-500 hover:bg-violet-600 text-white',
                  },
                ].map((item, i) => (
                  <div key={i} className={`card p-6 flex items-center justify-between gap-6 border-l-4 ${item.accent} ${item.bg} shadow-md hover:shadow-lg transition-shadow`}>
                    <div className="flex items-center gap-5 flex-1">
                      <div className="w-14 h-14 rounded-2xl bg-white bg-gray-800 flex items-center justify-center shadow-sm shrink-0">
                        {item.icon}
                      </div>
                      <div>
                        <h3 className="font-bold text-gray-800 text-gray-100 text-base mb-1">{item.title}</h3>
                        <p className="text-sm text-gray-500 text-gray-400 leading-relaxed">{item.desc}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(item.to)}
                      className={`shrink-0 px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${item.btnClass}`}
                    >
                      {item.btn} →
                    </button>
                  </div>
                ))}
              </div>
            </section>

            {/* Treatment Plan */}
            <div className="card p-6">
              <h2 className="font-semibold text-gray-900 text-white text-base mb-2">Your Personalized Treatment Plan</h2>
              <p className="text-sm text-gray-500 text-gray-400 leading-relaxed mb-4">
                Based on your health profile and AI analysis, we generate safe, step-by-step skin and scalp treatment recommendations tailored to you.
              </p>
              <button className="flex items-center gap-1.5 text-sm font-semibold text-blue-600 text-blue-400 transition">
                View treatment plan <ArrowRight size={15}/>
              </button>
            </div>

            {/* Makeup & Fashion */}
            <section>
              <p className="text-sm font-semibold text-gray-500 text-gray-400 mb-3">Makeup &amp; Fashion Assistance</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[
                  { icon: <Palette size={20}/>, title: 'Shade Matching' },
                  { icon: <Sparkles size={20}/>, title: 'Face-shape Styling Guidance' },
                ].map((item, i) => (
                  <button key={i} className="card p-5 flex items-center justify-between shadow-md transition-all text-left group">
                    <span className="font-semibold text-gray-800 text-gray-100">{item.title}</span>
                    <span className="text-gray-400 transition">{item.icon}</span>
                  </button>
                ))}
              </div>
            </section>

            {/* Today's Overview */}
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-gray-900 text-white">Today's overview</h2>
                <span className="text-xs text-gray-400">High-level snapshot of your activity</span>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'Last skin analysis', value: 'Not yet completed' },
                  { label: 'Next follow-up', value: 'Set after first diagnosis' },
                  { label: 'Reminders', value: '3 active treatment reminders' },
                ].map((item, i) => (
                  <div key={i}>
                    <p className="text-xs font-semibold text-gray-500 text-gray-400">{item.label}</p>
                    <p className="text-sm text-gray-700 text-gray-300 mt-0.5">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-5">

            {/* Book Appointment */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 text-white mb-1">Book Dermatologist / Salon Appointment</h2>
              <p className="text-xs text-gray-400 text-gray-500 mb-4">
                Connect with dermatology experts or salon & fashion services based on your diagnosis.
              </p>
              <div className="flex flex-wrap gap-2 mb-4">
                {['Dermatology', 'Salon', 'Fashion assistant'].map(tag => (
                  <span key={tag} className="bg-gray-100 bg-gray-800 text-gray-600 text-gray-300 text-xs font-medium px-3 py-1 rounded-full">{tag}</span>
                ))}
              </div>
              <button className="btn-secondary w-full">
                <Calendar size={15}/> Book an appointment
              </button>
            </div>

            {/* Notifications */}
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Bell size={17} className="text-blue-500"/>
                <h2 className="font-semibold text-gray-900 text-white">Notifications &amp; Reminders</h2>
              </div>
              <ul className="space-y-3">
                {notifications.map((n, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${n.color}`}/>
                    <span className="text-xs text-gray-600 text-gray-400 leading-relaxed">{n.text}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* AR Try-On */}
            <div className="card p-5">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h2 className="font-semibold text-gray-900 text-white">AR Try-On <span className="text-xs text-amber-500 font-bold ml-1">(Premium)</span></h2>
                  <p className="text-xs text-gray-400 text-gray-500 mt-1 leading-relaxed">
                    Secure, AI-assisted virtual try-on for makeup looks and hairstyles before real-world application.
                  </p>
                </div>
                <Grid size={20} className="text-gray-300 text-gray-600 shrink-0 ml-3"/>
              </div>
              <button className="btn-outline w-full mt-3 text-sm">
                <Sparkles size={14}/> Explore AR
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}