import { useNavigate } from 'react-router-dom';
import { Home } from 'lucide-react';
import Navbar from './Navbar';
import Footer from './Footer';
import './StaticPage.css';

export default function StaticPage({ title, subtitle, children, icon }) {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gray-50 bg-gray-950 flex flex-col">
      <Navbar title={title} />
      <main className="static-page-main">
        <div className="static-page-header">
          <div>
            {icon && <div className="static-page-icon">{icon}</div>}
            <h1 className="static-page-title">{title}</h1>
            {subtitle && <p className="static-page-sub">{subtitle}</p>}
          </div>
          <button onClick={() => navigate('/home')} className="btn-secondary text-sm py-2">
            <Home size={14}/> Home
          </button>
        </div>

        <div className="card static-page-body">
          {children}
        </div>
      </main>
      <Footer />
    </div>
  );
}
