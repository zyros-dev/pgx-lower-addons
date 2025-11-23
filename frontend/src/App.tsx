import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Banner from './components/Banner';
import Footer from './components/Footer';
import QueryPage from './pages/QueryPage';
import DocsPage from './pages/DocsPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Banner />
        <Routes>
          <Route path="/" element={<DocsPage />} />
          <Route path="/query" element={<QueryPage />} />
        </Routes>
        <Footer />
      </div>
    </Router>
  );
}

export default App;
