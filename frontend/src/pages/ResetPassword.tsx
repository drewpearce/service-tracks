import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient, ApiClientError } from "../api/client";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const token = searchParams.get("token") ?? "";

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        window.location.href = "/login";
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setValidationError(null);
    setApiError(null);

    if (password.length < 8) {
      setValidationError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setValidationError("Passwords do not match.");
      return;
    }

    try {
      await apiClient("/api/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password: password }),
      });
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 400) {
        setApiError("Invalid or expired link. Please request a new reset email.");
      } else {
        setApiError("Something went wrong. Please try again.");
      }
    }
  }

  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md rounded-lg bg-white p-8 shadow text-center">
          <h2 className="text-2xl font-bold text-green-700">Password reset!</h2>
          <p className="mt-2 text-gray-600">Redirecting to login…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h2 className="text-2xl font-bold text-gray-900">Reset your password</h2>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              New password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
              Confirm new password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          {validationError && <p className="text-sm text-red-600">{validationError}</p>}
          {apiError && <p className="text-sm text-red-600">{apiError}</p>}
          <button
            type="submit"
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Reset password
          </button>
        </form>
      </div>
    </div>
  );
}
