"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { loadUserProfile, saveUserProfile, type UserGender } from "@/lib/userProfile";

export default function HomePage() {
  const router = useRouter();
  const [showSignup, setShowSignup] = useState(false);
  const [name, setName] = useState("");
  const [gender, setGender] = useState<UserGender>("male");
  const [email, setEmail] = useState("");
  const [profession, setProfession] = useState("");
  const [error, setError] = useState("");

  function openAnalysisOrSignup() {
    const existing = loadUserProfile();
    if (existing) {
      router.push("/analysis");
      return;
    }
    setShowSignup(true);
  }

  function onSignup(e: FormEvent) {
    e.preventDefault();
    const n = name.trim();
    const em = email.trim();
    const pr = profession.trim();
    if (n.length < 2) {
      setError("Please enter a valid name.");
      return;
    }
    if (!em || !em.includes("@")) {
      setError("Please enter a valid email.");
      return;
    }
    if (pr.length < 2) {
      setError("Please enter your profession.");
      return;
    }
    saveUserProfile({
      name: n,
      gender,
      email: em,
      profession: pr,
      updatedAt: new Date().toISOString()
    });
    setShowSignup(false);
    router.push("/analysis");
  }

  return (
    <main className="landing-page">
      <header className="landing-nav">
        <div className="brand">WealthAI</div>
        <nav>
          <a>Markets</a>
          <a>Funds</a>
          <a>Portfolio</a>
          <a>Insights</a>
        </nav>
        <div className="nav-actions">
          <button className="ghost-btn" onClick={openAnalysisOrSignup}>Sign In</button>
        </div>
      </header>

      <section className="hero">
        <div className="hero-left">
          <p className="chip">SEC-Registered AI Advisor</p>
          <h1>Institutional-Grade Mutual Fund Intelligence</h1>
          <p className="subtitle">
            Navigate the complexity of global markets with precision. Our RAG-powered AI
            analyzes multiple funds to find the perfect fit for your portfolio.
          </p>
          <div className="hero-actions">
            <button className="primary-btn hero-cta" onClick={openAnalysisOrSignup}>
              <span className="click-hand">👉</span> Start Analysis
            </button>
          </div>
        </div>

        <div className="hero-right">
          <div className="hero-graphic">
            <img src="/api/hero-image" alt="Growth chart illustration" />
          </div>
          <div className="insight-card">
            <p>Live Insights</p>
            <strong>+12.4%</strong>
            <span>Q4 Growth Target</span>
          </div>
        </div>
      </section>

      {showSignup ? (
        <div className="modal-backdrop" onClick={() => setShowSignup(false)}>
          <div className="signup-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Start Analysis</h3>
            <p>Enter your details to continue.</p>
            <form onSubmit={onSignup}>
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} required />
              </label>
              <label>
                Gender
                <select value={gender} onChange={(e) => setGender(e.target.value as UserGender)}>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label>
                Email
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </label>
              <label>
                Profession
                <input value={profession} onChange={(e) => setProfession(e.target.value)} required />
              </label>
              {error ? <div className="form-error">{error}</div> : null}
              <div className="modal-actions">
                <button type="button" className="ghost-btn" onClick={() => setShowSignup(false)}>Cancel</button>
                <button type="submit" className="primary-btn small">Sign up</button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </main>
  );
}
