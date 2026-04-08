import { Link } from "react-router-dom";
import type { StreamingConnectionStatus } from "../types/api";

interface SetupChecklistProps {
  pco_connected: boolean;
  service_type_selected: boolean;
  streaming_connections: StreamingConnectionStatus[];
}

function CheckItem({
  done,
  label,
  actionTo,
  actionLabel,
}: {
  done: boolean;
  label: string;
  actionTo: string;
  actionLabel: string;
}) {
  return (
    <li className="flex items-center gap-3">
      {done ? (
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-green-600">
          ✓
        </span>
      ) : (
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-gray-200 text-gray-400">
          ○
        </span>
      )}
      <span className="flex-1 text-sm text-gray-700">{label}</span>
      {!done && (
        <Link
          to={actionTo}
          className="text-sm font-medium text-blue-600 hover:underline"
        >
          {actionLabel}
        </Link>
      )}
    </li>
  );
}

export default function SetupChecklist({
  pco_connected,
  service_type_selected,
  streaming_connections,
}: SetupChecklistProps) {
  const spotifyConnected = streaming_connections.some(
    (c) => c.platform === "spotify" && c.connected
  );

  const allDone = pco_connected && service_type_selected && spotifyConnected;
  if (allDone) return null;

  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="text-lg font-semibold text-gray-900">Setup checklist</h2>
      <p className="mt-1 text-sm text-gray-500">
        Complete these steps to start syncing playlists.
      </p>
      <ul className="mt-4 space-y-3">
        <CheckItem
          done={pco_connected}
          label="Connect Planning Center Online"
          actionTo="/setup/pco"
          actionLabel="Connect PCO"
        />
        <CheckItem
          done={service_type_selected}
          label="Select a service type in PCO"
          actionTo="/setup/pco"
          actionLabel="Select service type"
        />
        <CheckItem
          done={spotifyConnected}
          label="Connect Spotify"
          actionTo="/setup/streaming"
          actionLabel="Connect Spotify"
        />
      </ul>
    </div>
  );
}
