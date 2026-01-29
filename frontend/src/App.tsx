import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AnimatedBackground } from './components/AnimatedBackground';
import { Home } from './pages/Home';
import { Results } from './pages/Results';
import './App.css';

function App() {
  // Use basename for GitHub Pages deployment
  const basename = import.meta.env.BASE_URL;

  return (
    <BrowserRouter basename={basename}>
      <AnimatedBackground variant="default" />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
