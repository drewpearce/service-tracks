import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { apiClient, ApiClientError } from "../api/client";
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

  // Connect form
  const [appId, setAppId] = useState("");
  const [secret, setSecret] = useState("");
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [serviceTypes, setServiceTypes] = useState<ServiceType[] | null>(null);

  // Service type selection
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
          : {
              connected: true,
              auth_method: "api_key",
              status: "active",
              last_successful_call_at: null,
              service_type_id: null,
              service_type_name: null,
            }
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
      const response = await apiClient<SelectServiceTypeResponse>(
        "/api/pco/select-service-type",
        {
          method: "POST",
          body: JSON.stringify({ service_type_id: selectedServiceTypeId }),
        }
      );
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              service_type_id: response.service_type_id,
              service_type_name: response.service_type_name,
            }
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
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="rounded-lg bg-white p-6 shadow">
        <p className="text-sm text-red-600">{loadError}</p>
      </div>
    );
  }

  // Fully connected state
  if (status?.connected && status.service_type_id) {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">PCO Setup</h1>
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            <span className="text-sm font-medium text-green-700">Connected</span>
          </div>
          <p className="mt-2 text-sm text-gray-600">
            Service type:{" "}
            <strong>{status.service_type_name ?? status.service_type_id}</strong>
          </p>
        </div>
      </div>
    );
  }

  // Connected but service type not yet selected — show service type picker
  if ((status?.connected || serviceTypes) && serviceTypes) {
    return (
      <div className="max-w-xl space-y-4">
        <h1 className="text-2xl font-bold text-gray-900">PCO Setup</h1>
        <div className="rounded-lg bg-white p-6 shadow">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-green-500" />
            <span className="text-sm font-medium text-green-700">
              PCO credentials verified
            </span>
          </div>
          <h2 className="mt-4 text-base font-semibold text-gray-900">
            Select a service type
          </h2>
          <form onSubmit={handleSelectServiceType} className="mt-4 space-y-4">
            <div>
              <label
                htmlFor="service-type"
                className="block text-sm font-medium text-gray-700"
              >
                Service type
              </label>
              <select
                id="service-type"
                required
                value={selectedServiceTypeId}
                onChange={(e) => setSelectedServiceTypeId(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">— Select —</option>
                {serviceTypes.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name}
                  </option>
                ))}
              </select>
            </div>
            {selectError && <p className="text-sm text-red-600">{selectError}</p>}
            <button
              type="submit"
              disabled={selecting || !selectedServiceTypeId}
              className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {selecting ? "Saving…" : "Save service type"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Not connected state
  return (
    <div className="max-w-xl space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">PCO Setup</h1>
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-base font-semibold text-gray-900">
          Connect Planning Center Online
        </h2>
        <p className="mt-1 text-sm text-gray-600">
          Create a Personal Access Token in your PCO account, then enter your
          credentials below.{" "}
          <a
            href="https://api.planningcenteronline.com/oauth/applications"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Open PCO API settings ↗
          </a>
        </p>
        <ol className="mt-3 list-inside list-decimal space-y-1 text-sm text-gray-600">
          <li>Go to PCO API settings linked above.</li>
          <li>Click "New Personal Access Token".</li>
          <li>Enter a description and create the token.</li>
          <li>Copy the Application ID and Secret below.</li>
        </ol>
        <form onSubmit={handleConnect} className="mt-4 space-y-4">
          <div>
            <label
              htmlFor="app-id"
              className="block text-sm font-medium text-gray-700"
            >
              Application ID
            </label>
            <input
              id="app-id"
              type="text"
              required
              value={appId}
              onChange={(e) => setAppId(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="secret" className="block text-sm font-medium text-gray-700">
              Secret
            </label>
            <input
              id="secret"
              type="password"
              required
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          {connectError && <p className="text-sm text-red-600">{connectError}</p>}
          <button
            type="submit"
            disabled={connecting}
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {connecting ? "Connecting…" : "Connect PCO"}
          </button>
        </form>
      </div>
    </div>
  );
}
