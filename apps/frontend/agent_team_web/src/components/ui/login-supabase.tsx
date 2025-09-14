"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
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
  defaultMode?: "signin" | "signup";
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
  redirectUrl = "/",
  defaultMode = "signin",
}: LoginSupabaseProps) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSignUp, setIsSignUp] = useState(defaultMode === "signup");

  const { signIn, signUp } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const supabase = createClient();

  // Update isSignUp when defaultMode changes
  useEffect(() => {
    setIsSignUp(defaultMode === "signup");
  }, [defaultMode]);

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
    <section className="min-h-screen bg-background transition-colors duration-300">
      {/* Background Gradient Overlay - same as homepage */}
      <div className="fixed inset-0 bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.1)_10.5%,rgba(245,120,2,0.08)_16%,rgba(245,140,2,0.06)_17.5%,rgba(245,170,100,0.04)_25%,rgba(238,174,202,0.02)_40%,rgba(202,179,214,0.01)_65%,rgba(148,201,233,0.005)_100%)] dark:bg-[radial-gradient(125%_125%_at_50%_101%,rgba(245,87,2,0.05)_10.5%,rgba(245,120,2,0.04)_16%,rgba(245,140,2,0.03)_17.5%,rgba(245,170,100,0.02)_25%,rgba(238,174,202,0.01)_40%,rgba(202,179,214,0.005)_65%,rgba(148,201,233,0.002)_100%)] pointer-events-none" />

      <div className="relative z-10 flex h-screen items-center justify-center">
        <div className="border-muted bg-background/95 backdrop-blur-sm flex w-full max-w-sm flex-col items-center gap-y-8 rounded-md border px-6 py-12 shadow-md">
          <div className="flex flex-col items-center gap-y-2">
            {/* Logo */}
            <div className="flex items-center gap-1 lg:justify-start">
              <a href={logo.url}>
                {logo.src.startsWith('http') ? (
                  <Image
                    src={logo.src}
                    alt={logo.alt}
                    title={logo.title}
                    width={120}
                    height={40}
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
