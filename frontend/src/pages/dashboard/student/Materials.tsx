import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BookOpen, Search, Download, Eye, Filter } from "lucide-react";

export default function StudentMaterials() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Учебные материалы</h1>
          <p className="text-muted-foreground">Все материалы от ваших преподавателей</p>
        </div>
      </div>

      {/* Search and Filter */}
      <Card className="p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Поиск материалов..." className="pl-10" />
          </div>
          <Button variant="outline">
            <Filter className="w-4 h-4 mr-2" />
            Фильтры
          </Button>
        </div>
      </Card>

      {/* Materials Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {materials.map((material, index) => (
          <Card key={index} className="p-6 hover:border-primary transition-colors">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
                <BookOpen className="w-6 h-6 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold mb-1">{material.title}</h3>
                    <p className="text-sm text-muted-foreground">{material.teacher}</p>
                  </div>
                  <Badge variant={material.status === "new" ? "default" : "secondary"}>
                    {material.status === "new" ? "Новое" : "Просмотрено"}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground mb-4">{material.description}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                  <span>{material.subject}</span>
                  <span>•</span>
                  <span>{material.date}</span>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" className="flex-1">
                    <Eye className="w-4 h-4 mr-2" />
                    Открыть
                  </Button>
                  <Button size="sm" variant="outline">
                    <Download className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

const materials = [
  {
    title: "Тригонометрия: основные формулы",
    teacher: "Иванова М.П.",
    subject: "Математика",
    description: "Краткий конспект основных тригонометрических формул с примерами",
    date: "20 октября 2024",
    status: "new"
  },
  {
    title: "Решение логарифмических уравнений",
    teacher: "Иванова М.П.",
    subject: "Математика",
    description: "Пошаговое руководство по решению уравнений с логарифмами",
    date: "18 октября 2024",
    status: "viewed"
  },
  {
    title: "Геометрия: задачи на углы",
    teacher: "Петров А.С.",
    subject: "Геометрия",
    description: "Сборник задач с подробными решениями",
    date: "15 октября 2024",
    status: "viewed"
  },
  {
    title: "Производные сложных функций",
    teacher: "Иванова М.П.",
    subject: "Математика",
    description: "Теория и практика вычисления производных",
    date: "12 октября 2024",
    status: "viewed"
  }
];
