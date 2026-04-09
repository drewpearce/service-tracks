import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";

type Status = "loading" | "success" | "error";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token");
  const [status, setStatus] = useState<Status>(initialToken ? "loading" : "error");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      return;
    }

    apiClient<{ email_verified: boolean }>("/api/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then(() => setStatus("success"))
      .catch((err) => {
        if (err instanceof ApiClientError && err.status !== 401) {
          setStatus("error");
        } else {
          setStatus("error");
        }
      });
  }, [searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow">
        {status === "loading" && (
          <p className="text-center text-gray-600">Verifying your email…</p>
        )}
        {status === "success" && (
          <div className="text-center">
            <h2 className="text-2xl font-bold text-green-700">Email verified!</h2>
            <p className="mt-2 text-gray-600">
              You can now use all features of ServiceTracks.
            </p>
          </div>
        )}
        {status === "error" && (
          <div className="text-center">
            <h2 className="text-2xl font-bold text-red-700">Verification failed</h2>
            <p className="mt-2 text-gray-600">
              Invalid or expired link. Please request a new verification email.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
