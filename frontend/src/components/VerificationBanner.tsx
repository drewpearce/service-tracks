import { useState } from "react";
import { apiClient, ApiClientError } from "../api/client";

interface VerificationBannerProps {
  emailVerified: boolean;
}

export default function VerificationBanner({ emailVerified }: VerificationBannerProps) {
  const [message, setMessage] = useState<string | null>(null);

  if (emailVerified) return null;

  async function handleResend() {
    try {
      await apiClient("/api/auth/resend-verification", { method: "POST" });
      setMessage("Email sent!");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 429) {
        setMessage("Please wait a moment before resending.");
      } else {
        setMessage("Something went wrong. Please try again.");
      }
    }
  }

  return (
    <div className="bg-rose-50 border-b border-rose-200 px-6 py-2.5 flex items-center justify-center gap-3 text-[13px] text-rose-700">
      <span className="h-1.5 w-1.5 rounded-full bg-rose-500 flex-shrink-0" />
      <span>Please verify your email address.</span>
      {message ? (
        <span className="font-medium">{message}</span>
      ) : (
        <button
          onClick={() => void handleResend()}
          className="font-medium underline underline-offset-2 hover:text-rose-900"
        >
          Resend verification email
        </button>
      )}
    </div>
  );
}
