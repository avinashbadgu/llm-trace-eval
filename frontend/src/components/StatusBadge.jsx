import clsx from "clsx";

const MAP = {
  done:       "badge-green",
  pending:    "badge-gray",
  evaluating: "badge-blue",
  error:      "badge-red",
};

export default function StatusBadge({ status }) {
  return (
    <span className={clsx(MAP[status] ?? "badge-gray")}>
      {status}
    </span>
  );
}
