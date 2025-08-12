import { LoginSupabase } from "@/components/ui/login-supabase";

export default function LoginPage() {
  return (
    <LoginSupabase 
      heading="Welcome Back"
      logo={{
        url: "/",
        src: "/assistant/AlfieKnowledgeBaseQueryAssistantIcon.png",
        alt: "Agent Team",
        title: "Agent Team",
      }}
      buttonText="Sign In"
      googleText="Sign in with Google"
      signupText="Don't have an account?"
      redirectUrl="/workflow-editor"
    />
  );
}