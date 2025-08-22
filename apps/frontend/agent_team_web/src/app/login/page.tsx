"use client";

import { LoginSupabase } from "@/components/ui/login-supabase";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";

function LoginContent() {
  const searchParams = useSearchParams();
  const [defaultMode, setDefaultMode] = useState<"signin" | "signup">("signin");

  useEffect(() => {
    const mode = searchParams.get("mode");
    if (mode === "signup") {
      setDefaultMode("signup");
    } else if (mode === "signin") {
      setDefaultMode("signin");
    }
  }, [searchParams]);

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
      redirectUrl="/"
      defaultMode={defaultMode}
    />
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}