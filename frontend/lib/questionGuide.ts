export type QuestionGuideSection = {
  id: string;
  title: string;
  questions: readonly string[];
};

/** 20 factual questions in 4 sections (5 per section). */
export const QUESTION_GUIDE_SECTIONS: readonly QuestionGuideSection[] = [
  {
    id: "nav-basics",
    title: "NAV & basics",
    questions: [
      "What is the latest NAV of HDFC Mid Cap Fund Direct Growth?",
      "What is the NAV of HDFC ELSS Tax Saver Fund Direct Plan Growth?",
      "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?",
      "What is the expense ratio of HDFC Focused Fund Direct Growth?",
      "What is the AUM of HDFC Equity Fund Direct Growth?",
    ],
  },
  {
    id: "holdings",
    title: "Holdings",
    questions: [
      "What are the top 5 holdings in HDFC Focused Fund Direct Growth?",
      "What is ICICI Bank's weight in HDFC Focused Fund Direct Growth?",
      "Does HDFC Mid Cap Fund hold TCS? If yes, what percentage?",
      "Which sectors have the largest allocation in HDFC Equity Fund Direct Growth?",
      "What is HDFC Bank's holding weight in HDFC Large Cap Fund Direct Growth?",
    ],
  },
  {
    id: "returns",
    title: "Returns & metrics",
    questions: [
      "What were the 3-year historic returns for HDFC Large Cap Fund Direct Growth on a ₹5,000 monthly SIP?",
      "What is the 5-year return shown for HDFC Mid Cap Fund Direct Growth in the return calculator?",
      "How much would ₹60,000 invested over 1 year have become for HDFC Focused Fund Direct Growth?",
      "What is the rating shown for HDFC ELSS Tax Saver Fund Direct Plan Growth?",
      "How many holdings does HDFC Focused Fund Direct Growth have?",
    ],
  },
  {
    id: "compare",
    title: "Schemes & compare",
    questions: [
      "List all five HDFC schemes you can answer questions about.",
      "Compare the expense ratios of HDFC Mid Cap and HDFC Large Cap direct growth plans.",
      "What is the fund category of HDFC Mid Cap Fund Direct Growth?",
      "Which HDFC fund in your data has the highest AUM?",
      "What is the minimum SIP across all five HDFC schemes?",
    ],
  },
] as const;

export const QUESTION_GUIDE_HINT =
  "For more questions, see Question Guide in Settings.";
