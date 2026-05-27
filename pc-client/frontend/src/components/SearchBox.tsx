import { useState, useRef, useEffect } from "react";
import { Search as SearchIcon, Loader2 } from "lucide-react";
import { useDebounce } from "../hooks/useDebounce";
import { GameList } from "./GameList";
import type { GameItem } from "../types/api";

interface SearchBoxProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchBox({ onSearch, isLoading }: SearchBoxProps) {
  const [query, setQuery] = useState("");
  const debouncedQuery = useDebounce(query, 500);
  const prevQueryRef = useRef("");

  useEffect(() => {
    if (debouncedQuery.trim() && debouncedQuery !== prevQueryRef.current) {
      prevQueryRef.current = debouncedQuery;
      onSearch(debouncedQuery.trim());
    }
  }, [debouncedQuery, onSearch]);

  const handleSearchClick = () => {
    if (query.trim()) {
      prevQueryRef.current = query.trim();
      onSearch(query.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && query.trim()) {
      prevQueryRef.current = query.trim();
      onSearch(query.trim());
    }
  };

  return (
    <div className="relative w-full">
      {/* Input */}
      <div className="flex items-center h-12 bg-bg-card border border-divider rounded-lg overflow-hidden focus-within:border-accent transition-colors duration-150">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入游戏名称..."
          className="flex-1 h-full bg-transparent px-4 text-text-primary text-sm placeholder:text-text-secondary outline-none"
        />
        <button
          onClick={handleSearchClick}
          className="h-full px-4 flex items-center justify-center hover:bg-divider transition-colors duration-150"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 text-accent animate-spin" />
          ) : (
            <SearchIcon className="w-5 h-5 text-text-secondary" />
          )}
        </button>
      </div>
    </div>
  );
}
