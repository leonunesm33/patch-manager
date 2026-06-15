import { useState, useEffect } from "react";

const PAGE_SIZE = 20;

export function usePagination<T>(items: T[], pageSize = PAGE_SIZE) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [items.length]);

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;

  return {
    page: safePage,
    totalPages,
    setPage,
    pageItems: items.slice(start, start + pageSize),
    from: items.length === 0 ? 0 : start + 1,
    to: Math.min(start + pageSize, items.length),
    total: items.length,
  };
}

interface PaginationProps {
  page: number;
  totalPages: number;
  from: number;
  to: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, totalPages, from, to, total, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 0 2px",
        gap: 8,
      }}
    >
      <span className="muted" style={{ fontSize: 13 }}>
        {from}–{to} de {total}
      </span>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <button
          className="btn"
          disabled={page === 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          Anterior
        </button>
        <span style={{ padding: "0 6px", fontWeight: 600, fontSize: 13 }}>
          {page} / {totalPages}
        </span>
        <button
          className="btn"
          disabled={page === totalPages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          Proxima
        </button>
      </div>
    </div>
  );
}
