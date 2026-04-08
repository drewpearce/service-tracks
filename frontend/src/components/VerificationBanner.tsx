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
    <div className="bg-amber-100 px-4 py-3 text-center text-sm text-amber-800">
      Please verify your email address.{" "}
      {message ? (
        <span className="font-medium">{message}</span>
      ) : (
        <button
          onClick={handleResend}
          className="font-medium underline hover:text-amber-900"
        >
          Resend verification email
        </button>
      )}
    </div>
  );
}
