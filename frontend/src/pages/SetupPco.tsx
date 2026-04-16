import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiClient, ApiClientError } from "../api/client";
import { Hero, Input, Select } from "../components/ui";
import type {
  PcoConnectResponse,
  PcoStatusResponse,
  SelectServiceTypeResponse,
  ServiceType,
} from "../types/api";

export default function SetupPco() {
  const [status, setStatus] = useState<PcoStatusResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [appId, setAppId] = useState("");
  const [secret, setSecret] = useState("");
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [serviceTypes, setServiceTypes] = useState<ServiceType[] | null>(null);

  const [selectedServiceTypeId, setSelectedServiceTypeId] = useState("");
  const [selectError, setSelectError] = useState<string | null>(null);
  const [selecting, setSelecting] = useState(false);

  useEffect(() => {
    apiClient<PcoStatusResponse>("/api/pco/status")
      .then((s) => setStatus(s))
      .catch((err) => {
        if (err instanceof ApiClientError && err.status === 403) {
          setLoadError("Please verify your email before connecting PCO.");
        } else {
          setLoadError("Failed to load PCO status.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setConnectError(null);
    setConnecting(true);
    try {
      const response = await apiClient<PcoConnectResponse>("/api/pco/connect", {
        method: "POST",
        body: JSON.stringify({ application_id: appId, secret }),
      });
      setServiceTypes(response.service_types);
      setStatus((prev) =>
        prev
          ? { ...prev, connected: true, status: "active" }
          : { connected: true, auth_method: "api_key", status: "active", last_successful_call_at: null, service_type_id: null, service_type_name: null }
      );
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 400) {
          setConnectError("Invalid credentials. Please check your Application ID and Secret.");
        } else if (err.status === 403) {
          setConnectError("Please verify your email before connecting PCO.");
        } else {
          setConnectError("Something went wrong. Please try again.");
        }
      }
    } finally {
      setConnecting(false);
    }
  }

  async function handleSelectServiceType(e: FormEvent) {
    e.preventDefault();
    setSelectError(null);
    setSelecting(true);
    try {
      const response = await apiClient<SelectServiceTypeResponse>("/api/pco/select-service-type", {
        method: "POST",
        body: JSON.stringify({ service_type_id: selectedServiceTypeId }),
      });
      setStatus((prev) =>
        prev
          ? { ...prev, service_type_id: response.service_type_id, service_type_name: response.service_type_name }
          : prev
      );
      setServiceTypes(null);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 400) {
          setSelectError("Invalid service type. Please select again.");
        } else {
          setSelectError("Something went wrong. Please try again.");
        }
      }
    } finally {
      setSelecting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-500 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="px-10 py-10">
        <div className="rounded-2xl bg-white border border-slate-200 p-6">
          <p className="text-[14px] text-rose-600">{loadError}</p>
        </div>
      </div>
    );
  }

  // Fully connected
  if (status?.connected && status.service_type_id) {
    return (
      <>
        <Hero>
          <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
            Setup · PCO
          </p>
          <h1 className="font-display text-[40px] leading-[1.05] font-semibold tracking-tight">
            Planning Center
          </h1>
        </Hero>
        <div className="px-10 py-10 max-w-3xl">
          <div className="rounded-2xl bg-white border border-slate-200 p-6">
            <div className="flex items-center gap-3 mb-3">
              <span className="h-2 w-2 rounded-full bg-teal-500" />
              <span className="text-[14px] font-semibold text-teal-700">Connected</span>
            </div>
            <p className="text-[14px] text-slate-600">
              Service type:{" "}
              <span className="font-semibold text-slate-900">
                {status.service_type_name ?? status.service_type_id}
              </span>
            </p>
          </div>
        </div>
      </>
    );
  }

  // Connected, need service type
  if ((status?.connected || serviceTypes) && serviceTypes) {
    return (
      <>
        <Hero>
          <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
            Setup · PCO · Step 2
          </p>
          <h1 className="font-display text-[40px] leading-[1.05] font-semibold tracking-tight">
            Select a service type
          </h1>
          <p className="mt-3 max-w-xl text-[14px] text-slate-300">
            PCO credentials verified. Choose which service type to sync plans from.
          </p>
        </Hero>
        <div className="px-10 py-10 max-w-3xl">
          <div className="rounded-2xl bg-white border border-slate-200 p-8">
            <form onSubmit={handleSelectServiceType} className="space-y-6">
              <div>
                <label htmlFor="service-type" className="block text-[13px] font-medium text-slate-700 mb-1.5">
                  Service type
                </label>
                <Select
                  id="service-type"
                  required
                  value={selectedServiceTypeId}
                  onChange={(e) => setSelectedServiceTypeId(e.target.value)}
                >
                  <option value="">— Select —</option>
                  {serviceTypes.map((st) => (
                    <option key={st.id} value={st.id}>
                      {st.name}
                    </option>
                  ))}
                </Select>
              </div>
              {selectError && <p className="text-[13px] text-rose-600">{selectError}</p>}
              <button
                type="submit"
                disabled={selecting || !selectedServiceTypeId}
                className="rounded-full bg-slate-900 text-white px-6 py-2.5 text-[13px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
              >
                {selecting ? "Saving…" : "Save service type"}
              </button>
            </form>
          </div>
        </div>
      </>
    );
  }

  // Not connected
  return (
    <>
      <Hero>
        <p className="text-[12px] uppercase tracking-[0.25em] text-teal-400 font-semibold mb-3">
          Setup · PCO · Step 1
        </p>
        <h1 className="font-display text-[36px] leading-[1.1] font-semibold tracking-tight">
          Connect Planning Center Online
        </h1>
        <p className="mt-3 max-w-xl text-[14px] text-slate-300 leading-relaxed">
          Create a Personal Access Token in PCO and paste your credentials below.
        </p>
      </Hero>

      <div className="px-10 py-10 max-w-3xl">
        <div className="grid grid-cols-5 gap-8">
          {/* Instructions */}
          <aside className="col-span-2">
            <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500 font-semibold">
              Get your credentials
            </p>
            <h2 className="mt-2 font-display text-xl font-semibold tracking-tight text-slate-900">
              Create a Personal Access Token
            </h2>
            <ol className="mt-5 space-y-4 text-[13.5px] text-slate-600 leading-relaxed list-none">
              {[
                <>Go to <a href="https://api.planningcenteronline.com/oauth/applications" target="_blank" rel="noopener noreferrer" className="text-teal-600 hover:underline">PCO API settings ↗</a></>,
                'Click "New Personal Access Token".',
                "Enter a description and create the token.",
                "Copy the Application ID and Secret below.",
              ].map((step, i) => (
                <li key={i} className="flex gap-3">
                  <span className="flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </aside>

          {/* Form */}
          <div className="col-span-3">
            <div className="rounded-2xl bg-white border border-slate-200 p-8">
              <h2 className="font-display text-2xl font-semibold tracking-tight text-slate-900">
                Your PCO credentials
              </h2>
              <p className="mt-1 text-[13px] text-slate-500">
                Paste the Application ID and Secret from your Personal Access Token.
              </p>
              <form onSubmit={handleConnect} className="mt-6 space-y-5">
                <div>
                  <label htmlFor="app-id" className="block text-[13px] font-medium text-slate-700 mb-1.5">
                    Application ID
                  </label>
                  <Input
                    id="app-id"
                    type="text"
                    required
                    mono
                    placeholder="abc123…"
                    value={appId}
                    onChange={(e) => setAppId(e.target.value)}
                    error={!!connectError}
                  />
                </div>
                <div>
                  <label htmlFor="secret" className="block text-[13px] font-medium text-slate-700 mb-1.5">
                    Secret
                  </label>
                  <Input
                    id="secret"
                    type="password"
                    required
                    mono
                    placeholder="••••••••••••"
                    value={secret}
                    onChange={(e) => setSecret(e.target.value)}
                    error={!!connectError}
                  />
                </div>
                {connectError && (
                  <p className="text-[13px] text-rose-600">{connectError}</p>
                )}
                <button
                  type="submit"
                  disabled={connecting}
                  className="w-full rounded-full bg-slate-900 text-white py-3 text-[14px] font-semibold hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  {connecting ? "Connecting…" : "Connect PCO"}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
