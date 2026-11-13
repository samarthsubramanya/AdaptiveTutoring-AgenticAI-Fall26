import {
  ArrowUpRight,
  BookOpen,
  ChartColumn,
  Check,
  ChevronRight,
  CircleHelp,
  Compass,
  History,
  House,
  Lightbulb,
  Menu,
  MoveRight,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  ArrowRight,
  RotateCcw,
  LoaderCircle,
  ExternalLink,
  CheckCheck,
  SlidersHorizontal,
  TriangleAlert,
  Sigma,
  NotebookPen,
  Wifi,
  Download,
} from "lucide-react";
const icons = {
  ArrowUpRight,
  BookOpen,
  ChartColumn,
  Check,
  ChevronRight,
  CircleHelp,
  Compass,
  History,
  House,
  Lightbulb,
  Menu,
  MoveRight,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  ArrowRight,
  RotateCcw,
  LoaderCircle,
  ExternalLink,
  CheckCheck,
  SlidersHorizontal,
  TriangleAlert,
  Sigma,
  NotebookPen,
  Wifi,
  Download,
};
export type IconName = keyof typeof icons;
export default function Icon({
  name,
  size = 20,
  className = "",
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  const Component = icons[name];
  return (
    <Component
      size={size}
      strokeWidth={1.7}
      className={className}
      aria-hidden="true"
    />
  );
}
