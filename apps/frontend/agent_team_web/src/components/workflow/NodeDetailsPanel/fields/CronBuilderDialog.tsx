"use client";

import React, { useState, useEffect } from "react";
import { Calendar, Clock, Globe } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getUserTimezone, getTimezoneWithOffset } from "@/utils/timezone";

interface CronBuilderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialValue?: string;
  onConfirm: (cronExpression: string) => void;
}

export const CronBuilderDialog: React.FC<CronBuilderDialogProps> = ({
  open,
  onOpenChange,
  initialValue = "0 9 * * *",
  onConfirm,
}) => {
  const [minute, setMinute] = useState("0");
  const [hour, setHour] = useState("9");
  const [dayOfMonth, setDayOfMonth] = useState<string[]>(["*"]);
  const [month, setMonth] = useState<string[]>(["*"]);
  const [dayOfWeek, setDayOfWeek] = useState<string[]>(["*"]);

  // Parse initial cron expression when dialog opens
  useEffect(() => {
    if (open && initialValue) {
      const parts = initialValue.trim().split(/\s+/);
      if (parts.length >= 5) {
        setMinute(parts[0] || "0");
        setHour(parts[1] || "9");
        setDayOfMonth(parts[2] === "*" ? ["*"] : parts[2].split(","));
        setMonth(parts[3] === "*" ? ["*"] : parts[3].split(","));
        setDayOfWeek(parts[4] === "*" ? ["*"] : parts[4].split(","));
      }
    }
  }, [open, initialValue]);

  const joinValues = (vals: string[]) =>
    vals.includes("*") ? "*" : vals.join(",");

  const cronExpression = `${minute} ${hour} ${joinValues(dayOfMonth)} ${joinValues(month)} ${joinValues(dayOfWeek)}`;

  // Human-readable description (simplified version)
  const getHumanReadable = () => {
    try {
      const parts: string[] = [];

      // Minute
      if (minute === "*") {
        parts.push("every minute");
      } else {
        parts.push(`at minute ${minute}`);
      }

      // Hour
      if (hour === "*") {
        parts.push("of every hour");
      } else {
        parts.push(`at ${hour}:${minute.padStart(2, "0")}`);
      }

      // Day of month
      const domText = joinValues(dayOfMonth);
      if (domText !== "*") {
        parts.push(`on day(s) ${domText} of the month`);
      }

      // Month
      const monthText = joinValues(month);
      if (monthText !== "*") {
        const monthNames = [
          "Jan",
          "Feb",
          "Mar",
          "Apr",
          "May",
          "Jun",
          "Jul",
          "Aug",
          "Sep",
          "Oct",
          "Nov",
          "Dec",
        ];
        const monthList = month
          .filter((m) => m !== "*")
          .map((m) => monthNames[parseInt(m) - 1])
          .join(", ");
        parts.push(`in ${monthList}`);
      }

      // Day of week
      const dowText = joinValues(dayOfWeek);
      if (dowText !== "*") {
        const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        const dayList = dayOfWeek
          .filter((d) => d !== "*")
          .map((d) => dayNames[parseInt(d)])
          .join(", ");
        parts.push(`on ${dayList}`);
      }

      return parts.join(" ");
    } catch {
      return "Invalid expression";
    }
  };

  const toggleValue = (
    list: string[],
    setList: (vals: string[]) => void,
    value: string
  ) => {
    if (value === "*") {
      setList(["*"]);
      return;
    }
    let newList = [...list];
    if (newList.includes("*")) newList = [];
    if (newList.includes(value)) {
      newList = newList.filter((v) => v !== value);
    } else {
      newList.push(value);
    }
    if (newList.length === 0) newList = ["*"];
    setList(newList);
  };

  const applyPreset = (
    m: string,
    h: string,
    dom: string[],
    mon: string[],
    dow: string[]
  ) => {
    setMinute(m);
    setHour(h);
    setDayOfMonth(dom);
    setMonth(mon);
    setDayOfWeek(dow);
  };

  const handleConfirm = () => {
    onConfirm(cronExpression);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Cron Expression Builder
          </DialogTitle>
          <DialogDescription>
            Create a schedule using the visual builder or use preset options
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh]">
          <div className="space-y-4 pr-4">
            {/* Presets */}
            <div>
              <h4 className="text-sm font-medium mb-2">Quick Presets</h4>
              <div className="flex gap-2 flex-wrap">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset("0", "9", ["*"], ["*"], ["*"])}
                >
                  Every day at 9 AM
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset("0", "0", ["1"], ["*"], ["*"])}
                >
                  First of every month
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset("0", "9", ["*"], ["*"], ["1"])}
                >
                  Every Monday at 9 AM
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset("0", "0", ["*"], ["*"], ["*"])}
                >
                  Every day at midnight
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => applyPreset("0", "12", ["*"], ["*"], ["*"])}
                >
                  Every day at noon
                </Button>
              </div>
            </div>

            {/* Builder */}
            <Card>
              <CardContent className="pt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  {/* Minute */}
                  <div>
                    <label className="text-sm font-medium mb-1.5 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Minute
                    </label>
                    <Select value={minute} onValueChange={setMinute}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="*">Every minute</SelectItem>
                        <SelectItem value="0">:00</SelectItem>
                        <SelectItem value="15">:15</SelectItem>
                        <SelectItem value="30">:30</SelectItem>
                        <SelectItem value="45">:45</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Hour */}
                  <div>
                    <label className="text-sm font-medium mb-1.5 flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Hour
                    </label>
                    <Select value={hour} onValueChange={setHour}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="*">Every hour</SelectItem>
                        {Array.from({ length: 24 }).map((_, i) => (
                          <SelectItem key={i} value={i.toString()}>
                            {i.toString().padStart(2, "0")}:00
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Day of Month */}
                <div>
                  <label className="text-sm font-medium mb-1.5 block">
                    Day of Month (select multiple)
                  </label>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      type="button"
                      size="sm"
                      variant={
                        dayOfMonth.includes("*") ? "default" : "outline"
                      }
                      onClick={() => toggleValue(dayOfMonth, setDayOfMonth, "*")}
                    >
                      Every day
                    </Button>
                    {[...Array(31).keys()].map((d) => (
                      <Button
                        key={d + 1}
                        type="button"
                        size="sm"
                        variant={
                          dayOfMonth.includes((d + 1).toString())
                            ? "default"
                            : "outline"
                        }
                        onClick={() =>
                          toggleValue(
                            dayOfMonth,
                            setDayOfMonth,
                            (d + 1).toString()
                          )
                        }
                        className="w-9"
                      >
                        {d + 1}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Month */}
                <div>
                  <label className="text-sm font-medium mb-1.5 block">
                    Month (select multiple)
                  </label>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      type="button"
                      size="sm"
                      variant={month.includes("*") ? "default" : "outline"}
                      onClick={() => toggleValue(month, setMonth, "*")}
                    >
                      Every month
                    </Button>
                    {[
                      "Jan",
                      "Feb",
                      "Mar",
                      "Apr",
                      "May",
                      "Jun",
                      "Jul",
                      "Aug",
                      "Sep",
                      "Oct",
                      "Nov",
                      "Dec",
                    ].map((label, idx) => (
                      <Button
                        key={idx + 1}
                        type="button"
                        size="sm"
                        variant={
                          month.includes((idx + 1).toString())
                            ? "default"
                            : "outline"
                        }
                        onClick={() =>
                          toggleValue(month, setMonth, (idx + 1).toString())
                        }
                      >
                        {label}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Day of Week */}
                <div>
                  <label className="text-sm font-medium mb-1.5 block">
                    Day of Week (select multiple)
                  </label>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      type="button"
                      size="sm"
                      variant={dayOfWeek.includes("*") ? "default" : "outline"}
                      onClick={() => toggleValue(dayOfWeek, setDayOfWeek, "*")}
                    >
                      Every day
                    </Button>
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
                      (label, idx) => (
                        <Button
                          key={idx}
                          type="button"
                          size="sm"
                          variant={
                            dayOfWeek.includes(idx.toString())
                              ? "default"
                              : "outline"
                          }
                          onClick={() =>
                            toggleValue(
                              dayOfWeek,
                              setDayOfWeek,
                              idx.toString()
                            )
                          }
                        >
                          {label}
                        </Button>
                      )
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Preview */}
            <Card className="bg-muted/50">
              <CardContent className="pt-4 space-y-2">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Cron Expression:
                  </p>
                  <p className="font-mono text-sm font-medium">
                    {cronExpression}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Schedule:
                  </p>
                  <p className="text-sm text-foreground">{getHumanReadable()}</p>
                </div>
                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                    <Globe className="h-3 w-3" />
                    Timezone:
                  </p>
                  <p className="text-sm text-foreground font-medium">
                    {getTimezoneWithOffset()}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Times will be executed in your local timezone
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm}>
            Apply Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
