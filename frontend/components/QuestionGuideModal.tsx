"use client";

import { useEffect, useState } from "react";
import { QUESTION_GUIDE_SECTIONS } from "@/lib/questionGuide";

type Props = {
  open: boolean;
  busy?: boolean;
  onClose: () => void;
  onPickQuestion: (question: string) => void;
};

export function QuestionGuideModal({ open, busy, onClose, onPickQuestion }: Props) {
  const [sectionIndex, setSectionIndex] = useState(0);

  useEffect(() => {
    if (open) setSectionIndex(0);
  }, [open]);

  if (!open) return null;

  const section = QUESTION_GUIDE_SECTIONS[sectionIndex];
  const totalSections = QUESTION_GUIDE_SECTIONS.length;

  function goPrev() {
    setSectionIndex((i) => Math.max(0, i - 1));
  }

  function goNext() {
    setSectionIndex((i) => Math.min(totalSections - 1, i + 1));
  }

  return (
    <div className="modal-backdrop question-guide-backdrop" onClick={onClose}>
      <div
        className="question-guide-modal"
        role="dialog"
        aria-labelledby="question-guide-title"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="question-guide-header">
          <div>
            <h3 id="question-guide-title">Question guide</h3>
            <p className="question-guide-sub">
              Section {sectionIndex + 1} of {totalSections} · {section.title}
            </p>
          </div>
          <button
            type="button"
            className="question-guide-close"
            onClick={onClose}
            aria-label="Close question guide"
          >
            ×
          </button>
        </div>

        <ul className="question-guide-list">
          {section.questions.map((q) => (
            <li key={q}>
              <button
                type="button"
                className="question-guide-item"
                disabled={busy}
                onClick={() => onPickQuestion(q)}
              >
                {q}
              </button>
            </li>
          ))}
        </ul>

        <div className="question-guide-nav">
          <button
            type="button"
            className="ghost-btn question-guide-nav-btn"
            disabled={sectionIndex === 0}
            onClick={goPrev}
          >
            ← Previous
          </button>
          <span className="question-guide-dots" aria-hidden="true">
            {QUESTION_GUIDE_SECTIONS.map((s, i) => (
              <span key={s.id} className={i === sectionIndex ? "active" : ""} />
            ))}
          </span>
          <button
            type="button"
            className="ghost-btn question-guide-nav-btn"
            disabled={sectionIndex >= totalSections - 1}
            onClick={goNext}
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
