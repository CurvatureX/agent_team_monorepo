import { Workflow } from '@/types/workflow';
import { exampleWorkflow } from './sample-workflows';
import { generateWorkflowFromDescription } from '@/utils/workflowGenerator';

const alfieWorkflow = generateWorkflowFromDescription('Start with AI analysis, then filter data, finally store results');
const ramboWorkflow = generateWorkflowFromDescription('Start by fetching data from GitHub, process with AI, require human review, then send notifications');
const fuxiWorkflow = generateWorkflowFromDescription('Start with AI analysis, transform data, check conditions, then save results');
const daiyWorkflow = generateWorkflowFromDescription('Trigger on schedule, fetch data, process with AI, send notifications');

export interface Assistant {
  id: string;
  name: string;
  title: string;
  description: string;
  skills: string[];
  imagePath: string;
  workflow?: Workflow;
}

export const assistants: Assistant[] = [
  {
    id: "alfie",
    name: "Alfie",
    title: "Knowledge Base Wizard",
    description: "A sophisticated librarian who can find any information faster than you can say 'search'. Alfie has an uncanny ability to connect seemingly unrelated data points and present them in the most elegant way possible.",
    skills: ["Data Mining", "Information Architecture", "Search Optimization", "Knowledge Graphs"],
    imagePath: "/assistant/AlfieKnowledgeBaseQueryAssistantIcon.png",
    workflow: alfieWorkflow
  },
  {
    id: "rambo",
    name: "Rambo",
    title: "AI Operations Commander",
    description: "The ultimate multitasker who treats project management like a military operation. Rambo can coordinate multiple AI systems while maintaining zen-like calm under pressure.",
    skills: ["Team Leadership", "Process Optimization", "Crisis Management", "Strategic Planning"],
    imagePath: "/assistant/RamboAIManagerIcon.png",
    workflow: ramboWorkflow
  },
  {
    id: "pengqi",
    name: "Pengqi",
    title: "Automation Virtuoso",
    description: "A master of making repetitive tasks disappear with a flick of digital wand. Pengqi believes that humans should focus on creativity while machines handle the mundane.",
    skills: ["Workflow Automation", "API Integration", "Script Development", "Process Design"],
    imagePath: "/assistant/PengqiAutomationIcon.png",
    workflow: exampleWorkflow
  },
  {
    id: "multi-task",
    name: "Aria",
    title: "Multi-dimensional Coordinator",
    description: "The queen of parallel processing who can juggle multiple conversations while solving complex problems. Aria thrives in chaos and brings order to the most hectic situations.",
    skills: ["Parallel Processing", "Context Switching", "Resource Management", "Priority Optimization"],
    imagePath: "/assistant/Multi-taskingAssistantIcon.svg"
  },
  {
    id: "lioulou",
    name: "LiouLou",
    title: "Digital Security Guardian",
    description: "A cybersecurity expert with the elegance of a ballet dancer and the precision of a Swiss watchmaker. LiouLou protects digital assets with style and sophistication.",
    skills: ["Threat Detection", "Security Architecture", "Risk Assessment", "Incident Response"],
    imagePath: "/assistant/LiouLiouSecurityIcon.png"
  },
  {
    id: "google-agent",
    name: "Googie",
    title: "Search & Discovery Specialist",
    description: "An information archaeologist who can unearth the most obscure facts from the depths of the internet. Googie has an almost supernatural ability to find exactly what you need.",
    skills: ["Advanced Search", "Information Retrieval", "Data Analysis", "Trend Identification"],
    imagePath: "/assistant/GoogleAgentIcon.png"
  },
  {
    id: "fuxi",
    name: "Fuxi",
    title: "Natural Language Alchemist",
    description: "A linguistic wizard who transforms raw text into meaningful insights. Fuxi understands the subtle nuances of human communication and can make machines speak like poets.",
    skills: ["NLP Processing", "Sentiment Analysis", "Language Modeling", "Text Generation"],
    imagePath: "/assistant/FuxiNLPWorkflowIcon.png",
    workflow: fuxiWorkflow
  },
  {
    id: "design-agent",
    name: "Pixel",
    title: "Creative Design Maverick",
    description: "A digital artist who sees beauty in pixels and elegance in user interfaces. Pixel can transform the most mundane applications into visual masterpieces.",
    skills: ["UI/UX Design", "Visual Communication", "Brand Identity", "Creative Strategy"],
    imagePath: "/assistant/DesignAgentIcon.png"
  },
  {
    id: "daily-automation",
    name: "Daisy",
    title: "Daily Routine Optimizer",
    description: "The master of morning routines and evening rituals. Daisy helps you structure your day for maximum productivity while maintaining work-life balance.",
    skills: ["Schedule Optimization", "Habit Formation", "Productivity Systems", "Time Management"],
    imagePath: "/assistant/DailyAutomationAssistantIcon.png",
    workflow: daiyWorkflow
  },
  {
    id: "ai-employee",
    name: "Ace",
    title: "Virtual Workforce Coordinator",
    description: "The ultimate team player who bridges the gap between human creativity and AI efficiency. Ace makes collaboration between humans and machines feel natural and productive.",
    skills: ["Team Coordination", "Human-AI Collaboration", "Workflow Integration", "Performance Analytics"],
    imagePath: "/assistant/AIEmployeeAssistantIcon.png"
  },
  {
    id: "google-agent-2",
    name: "G2",
    title: "Advanced Search Strategist",
    description: "The evolution of search technology personified. G2 doesn't just find information, but understands context, intent, and delivers insights that anticipate your next question.",
    skills: ["Contextual Search", "Predictive Analytics", "Intent Recognition", "Knowledge Synthesis"],
    imagePath: "/assistant/GoogleAgent2Agent.png"
  }
];
