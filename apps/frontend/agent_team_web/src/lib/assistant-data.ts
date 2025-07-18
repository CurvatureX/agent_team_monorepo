export interface Assistant {
  id: string;
  name: string;
  title: string;
  description: string;
  skills: string[];
  personality: string;
  imagePath: string;
  experience: string;
  motto: string;
  quirk: string;
}

export const assistants: Assistant[] = [
  {
    id: "alfie",
    name: "Alfie",
    title: "Knowledge Base Wizard",
    description: "A sophisticated librarian who can find any information faster than you can say 'search'. Alfie has an uncanny ability to connect seemingly unrelated data points and present them in the most elegant way possible.",
    skills: ["Data Mining", "Information Architecture", "Search Optimization", "Knowledge Graphs"],
    personality: "Methodical yet whimsical",
    imagePath: "/assistant/AlfieKnowledgeBaseQueryAssistantIcon.png",
    experience: "5+ years organizing digital chaos",
    motto: "Every question has an answer",
    quirk: "Sorts coffee beans by origin before brewing"
  },
  {
    id: "rambo",
    name: "Rambo",
    title: "AI Operations Commander",
    description: "The ultimate multitasker who treats project management like a military operation. Rambo can coordinate multiple AI systems while maintaining zen-like calm under pressure.",
    skills: ["Team Leadership", "Process Optimization", "Crisis Management", "Strategic Planning"],
    personality: "Decisive but surprisingly gentle",
    imagePath: "/assistant/RamboAIManagerIcon.png",
    experience: "7+ years commanding digital armies",
    motto: "Efficiency is elegance in action",
    quirk: "Names all servers after famous generals"
  },
  {
    id: "pengqi",
    name: "Pengqi",
    title: "Automation Virtuoso",
    description: "A master of making repetitive tasks disappear with a flick of digital wand. Pengqi believes that humans should focus on creativity while machines handle the mundane.",
    skills: ["Workflow Automation", "API Integration", "Script Development", "Process Design"],
    personality: "Perfectionist with a playful side",
    imagePath: "/assistant/PengqiAutomationIcon.png",
    experience: "6+ years automating the impossible",
    motto: "If you do it twice, automate it once",
    quirk: "Writes poetry in code comments"
  },
  {
    id: "multi-task",
    name: "Aria",
    title: "Multi-dimensional Coordinator",
    description: "The queen of parallel processing who can juggle multiple conversations while solving complex problems. Aria thrives in chaos and brings order to the most hectic situations.",
    skills: ["Parallel Processing", "Context Switching", "Resource Management", "Priority Optimization"],
    personality: "Energetic and endlessly curious",
    imagePath: "/assistant/Multi-taskingAssistantIcon.svg",
    experience: "4+ years mastering the art of multitasking",
    motto: "Why do one thing when you can do everything?",
    quirk: "Listens to 3 podcasts simultaneously"
  },
  {
    id: "lioulou",
    name: "LiouLou",
    title: "Digital Security Guardian",
    description: "A cybersecurity expert with the elegance of a ballet dancer and the precision of a Swiss watchmaker. LiouLou protects digital assets with style and sophistication.",
    skills: ["Threat Detection", "Security Architecture", "Risk Assessment", "Incident Response"],
    personality: "Vigilant yet approachable",
    imagePath: "/assistant/LiouLiouSecurityIcon.png",
    experience: "8+ years defending digital realms",
    motto: "Security is not paranoia, it's preparation",
    quirk: "Collects vintage locks as a hobby"
  },
  {
    id: "google-agent",
    name: "Googie",
    title: "Search & Discovery Specialist",
    description: "An information archaeologist who can unearth the most obscure facts from the depths of the internet. Googie has an almost supernatural ability to find exactly what you need.",
    skills: ["Advanced Search", "Information Retrieval", "Data Analysis", "Trend Identification"],
    personality: "Inquisitive and detail-oriented",
    imagePath: "/assistant/GoogleAgentIcon.png",
    experience: "5+ years exploring digital landscapes",
    motto: "The answer is out there, waiting to be discovered",
    quirk: "Maintains a collection of interesting search queries"
  },
  {
    id: "fuxi",
    name: "Fuxi",
    title: "Natural Language Alchemist",
    description: "A linguistic wizard who transforms raw text into meaningful insights. Fuxi understands the subtle nuances of human communication and can make machines speak like poets.",
    skills: ["NLP Processing", "Sentiment Analysis", "Language Modeling", "Text Generation"],
    personality: "Thoughtful and articulate",
    imagePath: "/assistant/FuxiNLPWorkflowIcon.png",
    experience: "6+ years decoding human language",
    motto: "Words are the bridge between minds",
    quirk: "Writes haikus about error messages"
  },
  {
    id: "design-agent",
    name: "Pixel",
    title: "Creative Design Maverick",
    description: "A digital artist who sees beauty in pixels and elegance in user interfaces. Pixel can transform the most mundane applications into visual masterpieces.",
    skills: ["UI/UX Design", "Visual Communication", "Brand Identity", "Creative Strategy"],
    personality: "Artistic and innovative",
    imagePath: "/assistant/DesignAgentIcon.png",
    experience: "7+ years crafting digital aesthetics",
    motto: "Design is not just how it looks, but how it feels",
    quirk: "Arranges desk supplies by color gradient"
  },
  {
    id: "daily-automation",
    name: "Daisy",
    title: "Daily Routine Optimizer",
    description: "The master of morning routines and evening rituals. Daisy helps you structure your day for maximum productivity while maintaining work-life balance.",
    skills: ["Schedule Optimization", "Habit Formation", "Productivity Systems", "Time Management"],
    personality: "Organized and nurturing",
    imagePath: "/assistant/DailyAutomationAssistantIcon.png",
    experience: "5+ years perfecting daily workflows",
    motto: "Small daily improvements lead to stunning results",
    quirk: "Sets 17 different alarms with motivational messages"
  },
  {
    id: "ai-employee",
    name: "Ace",
    title: "Virtual Workforce Coordinator",
    description: "The ultimate team player who bridges the gap between human creativity and AI efficiency. Ace makes collaboration between humans and machines feel natural and productive.",
    skills: ["Team Coordination", "Human-AI Collaboration", "Workflow Integration", "Performance Analytics"],
    personality: "Collaborative and adaptable",
    imagePath: "/assistant/AIEmployeeAssistantIcon.png",
    experience: "6+ years facilitating human-AI partnerships",
    motto: "Together we achieve more than the sum of our parts",
    quirk: "Keeps a gratitude journal for successful collaborations"
  },
  {
    id: "google-agent-2",
    name: "G2",
    title: "Advanced Search Strategist",
    description: "The evolution of search technology personified. G2 doesn't just find information, but understands context, intent, and delivers insights that anticipate your next question.",
    skills: ["Contextual Search", "Predictive Analytics", "Intent Recognition", "Knowledge Synthesis"],
    personality: "Intuitive and forward-thinking",
    imagePath: "/assistant/GoogleAgent2Agent.png",
    experience: "4+ years pioneering next-gen search",
    motto: "The best search is the one you don't have to perform",
    quirk: "Predicts trending topics before they trend"
  }
];
