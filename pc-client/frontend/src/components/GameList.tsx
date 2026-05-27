import { Check, Search } from "lucide-react";
import type { GameItem } from "../types/api";

interface GameListProps {
  games: GameItem[];
  onSelect: (game: GameItem) => void;
  selectedUrl?: string;
}

function Skeleton() {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-card animate-pulse">
      <div className="w-16 h-16 rounded bg-divider" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-3/4 rounded bg-divider" />
        <div className="h-3 w-1/2 rounded bg-divider" />
      </div>
    </div>
  );
}

export function GameList({ games, onSelect, selectedUrl }: GameListProps) {
  if (games.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Search className="w-12 h-12 text-text-secondary opacity-40" />
        <p className="text-text-secondary text-sm">
          未找到匹配游戏，试试其他关键词
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {games.map((game, index) => {
        const isSelected = selectedUrl === game.source_url;

        return (
          <div
            key={`${game.source_url}-${index}`}
            onClick={() => onSelect(game)}
            className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors duration-150 ${
              isSelected
                ? "bg-accent/10 border border-accent/30"
                : "bg-bg-card hover:bg-bg-card/80 border border-transparent"
            }`}
          >
            {/* Cover placeholder */}
            <div className="w-16 h-16 rounded bg-divider flex-shrink-0 flex items-center justify-center">
              <span className="text-xs text-text-secondary">🎮</span>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-text-primary text-sm font-medium truncate">
                  {game.title}
                </span>
                {isSelected && (
                  <Check className="w-4 h-4 text-success flex-shrink-0" />
                )}
              </div>
              <div className="flex items-center gap-3 mt-1">
                {game.version && (
                  <span className="text-xs text-text-secondary">{game.version}</span>
                )}
                {game.size && (
                  <span className="text-xs text-text-secondary">{game.size}</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
