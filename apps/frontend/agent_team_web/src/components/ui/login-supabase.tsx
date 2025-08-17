"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FcGoogle } from "react-icons/fc";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { createClient } from "@/lib/supabase/client";

interface LoginSupabaseProps {
  heading?: string;
  logo?: {
    url: string;
    src: string;
    alt: string;
    title?: string;
  };
  buttonText?: string;
  googleText?: string;
  signupText?: string;
  redirectUrl?: string;
}

const LoginSupabase = ({
  heading = "Welcome Back",
  logo = {
    url: "/",
    src: "/logo.png",
    alt: "logo",
    title: "Agent Team",
  },
  buttonText = "Sign In",
  googleText = "Sign in with Google",
  signupText = "Don't have an account?",
  redirectUrl = "/workflow-editor",
}: LoginSupabaseProps) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  
  const { signIn, signUp } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const supabase = createClient();

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email || !password) {
      toast({
        title: "Error",
        description: "Please enter email and password",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);

    try {
      if (isSignUp) {
        const { error } = await signUp(email, password);
        if (error) {
          toast({
            title: "Sign up failed",
            description: error.message,
            variant: "destructive",
          });
        } else {
          toast({
            title: "Success!",
            description: "Please check your email to confirm your account.",
          });
          setIsSignUp(false);
        }
      } else {
        const { error } = await signIn(email, password);
        if (error) {
          toast({
            title: "Sign in failed",
            description: error.message,
            variant: "destructive",
          });
        } else {
          toast({
            title: "Welcome back!",
            description: "Successfully signed in.",
          });
          router.push(redirectUrl);
        }
      }
    } catch {
      toast({
        title: "Error",
        description: "An unexpected error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    try {
      setIsLoading(true);
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/supabase-callback`,
        },
      });

      if (error) {
        toast({
          title: "Error",
          description: error.message,
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to sign in with Google",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <section className="bg-muted bg-background h-screen">
      <div className="flex h-full items-center justify-center">
        <div className="border-muted bg-background flex w-full max-w-sm flex-col items-center gap-y-8 rounded-md border px-6 py-12 shadow-md">
          <div className="flex flex-col items-center gap-y-2">
            {/* Logo */}
            <div className="flex items-center gap-1 lg:justify-start">
              <a href={logo.url}>
                {logo.src.startsWith('http') ? (
                  <img
                    src={logo.src}
                    alt={logo.alt}
                    title={logo.title}
                    className="h-10 dark:invert"
                  />
                ) : (
                  <div className="text-2xl font-bold">{logo.title}</div>
                )}
              </a>
            </div>
            <h1 className="text-3xl font-semibold">
              {isSignUp ? "Create Account" : heading}
            </h1>
          </div>
          
          <form onSubmit={handleEmailAuth} className="flex w-full flex-col gap-8">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Input 
                  type="email" 
                  placeholder="Email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required 
                />
              </div>
              <div className="flex flex-col gap-2">
                <Input 
                  type="password" 
                  placeholder="Password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  required 
                />
              </div>
              <div className="flex flex-col gap-4">
                <Button 
                  type="submit" 
                  className="mt-2 w-full"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {isSignUp ? "Creating Account..." : "Signing In..."}
                    </>
                  ) : (
                    isSignUp ? "Sign Up" : buttonText
                  )}
                </Button>
                
                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">
                      Or continue with
                    </span>
                  </div>
                </div>
                
                <Button 
                  type="button"
                  variant="outline" 
                  className="w-full"
                  onClick={handleGoogleAuth}
                  disabled={isLoading}
                >
                  <FcGoogle className="mr-2 size-5" />
                  {googleText}
                </Button>
              </div>
            </div>
          </form>
          
          <div className="text-muted-foreground flex justify-center gap-1 text-sm">
            <p>{isSignUp ? "Already have an account?" : signupText}</p>
            <button
              onClick={() => setIsSignUp(!isSignUp)}
              className="text-primary font-medium hover:underline"
              disabled={isLoading}
            >
              {isSignUp ? "Sign In" : "Sign Up"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

export { LoginSupabase };