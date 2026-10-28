import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FlaskConical, Plus } from "lucide-react";
import { Button } from "../components/ui/button";
import { post } from "./api";

export function DemoBanner() {
  const client = useQueryClient();
  const advance = useMutation({
    mutationFn: () => post("/demo/advance", {}),
    onSuccess: () => {
      void client.invalidateQueries();
    },
  });
  return (
    <div
      className="demo-banner"
      role="region"
      aria-label="Демонстрационный режим"
    >
      <FlaskConical size={21} />
      <div>
        <strong>ДЕМО · вымышленные данные</strong>
        <p>
          Игра не подключена. Отдельная база data-demo; реальная история не
          изменяется.
        </p>
        {advance.isSuccess && (
          <p role="status">
            Демоснимок в очереди — показатели обновятся автоматически.
          </p>
        )}
        {advance.error && <p role="alert">{advance.error.message}</p>}
      </div>
      <Button
        variant="outline"
        disabled={advance.isPending}
        onClick={() => advance.mutate()}
      >
        <Plus size={15} />
        Следующий демоснимок
      </Button>
    </div>
  );
}
