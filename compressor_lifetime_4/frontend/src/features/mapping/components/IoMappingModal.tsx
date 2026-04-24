import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Save, ShieldAlert, X } from "lucide-react";

import type {
  LogicalSignal,
  StationIoMapping,
  ValidateMappingResponse,
} from "../../../shared/types/contracts";
import { toErrorMessage } from "../../../shared/utils/errors";
import {
  fetchHardwareCapabilities,
  listIoTemplates,
  saveIoTemplate,
  saveStationMapping,
  validateStationMapping,
} from "../api/mappingApi";

const SIGNALS: LogicalSignal[] = ["V1", "V2", "V3", "COMPRESSOR", "P_SENSOR", "COUNTER_PWR", "COUNTER_SIG", "BUZZER"];

type Props = {
  stationId: number;
  mapping: StationIoMapping;
  onClose: () => void;
  onSaved: (mapping: StationIoMapping) => void;
};

export function IoMappingModal({ stationId, mapping, onClose, onSaved }: Props) {
  const [draft, setDraft] = useState<StationIoMapping>(mapping);
  const [capabilities, setCapabilities] = useState<Awaited<ReturnType<typeof fetchHardwareCapabilities>> | null>(null);
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof listIoTemplates>>>([]);
  const [validation, setValidation] = useState<ValidateMappingResponse | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchHardwareCapabilities(draft.bindings.V1.device), listIoTemplates()])
      .then(([cap, list]) => {
        setCapabilities(cap);
        setTemplates(list);
      })
      .catch((err) => {
        setErrorMessage(toErrorMessage(err));
      });
  }, []);

  const channelOptions = useMemo(() => {
    if (!capabilities) {
      return [];
    }
    return capabilities.details.flatMap((item) =>
      item.channels.map((ch) => ({
        moduleType: item.moduleType,
        direction: item.direction,
        channel: ch,
      })),
    );
  }, [capabilities]);

  const localConflicts = useMemo(() => {
    const keyCount = new Map<string, number>();
    SIGNALS.forEach((signal) => {
      const ref = draft.bindings[signal];
      const key = `${ref.device}:${ref.moduleType}:${ref.channel}`;
      keyCount.set(key, (keyCount.get(key) ?? 0) + 1);
    });
    return new Set(Array.from(keyCount.entries()).filter(([, count]) => count > 1).map(([key]) => key));
  }, [draft]);

  const validateRemote = async () => {
    try {
      const result = await validateStationMapping(stationId, draft);
      setValidation(result);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(toErrorMessage(err));
    }
  };

  const save = async () => {
    try {
      const saved = await saveStationMapping(stationId, draft);
      onSaved(saved);
      onClose();
    } catch (err) {
      setErrorMessage(toErrorMessage(err));
    }
  };

  const saveTemplate = async () => {
    const cleanName = templateName.trim();
    const templateId = cleanName.replace(/\s+/g, "-").toLowerCase();
    if (!templateId) {
      return;
    }
    try {
      await saveIoTemplate({ templateId, name: cleanName, bindings: draft.bindings });
      const list = await listIoTemplates();
      setTemplates(list);
      setErrorMessage(null);
    } catch (err) {
      setErrorMessage(toErrorMessage(err));
    }
  };

  const applyTemplate = (templateId: string) => {
    const tmpl = templates.find((t) => t.templateId === templateId);
    if (!tmpl) {
      return;
    }
    setDraft((prev) => ({ ...prev, templateId: tmpl.templateId, bindings: tmpl.bindings }));
  };

  return (
    <div className="fixed inset-0 z-[9997] flex items-center justify-center bg-black/60 p-5 backdrop-blur-sm">
      <div className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-[30px] border border-white/15 bg-gradient-to-b from-[#1a1f2b] to-[#0f1118] text-white shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <div>
            <div className="text-lg font-black tracking-wide">Station {String(stationId).padStart(2, "0")} IO Mapping</div>
            <div className="text-xs text-white/45">Signal to physical channel binding</div>
          </div>
          <button onClick={onClose} className="rounded-full border border-white/20 bg-white/5 p-2 text-white/70 hover:bg-white/10 hover:text-white">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 px-6 py-4 lg:grid-cols-[1fr_auto]">
          <div className="flex flex-wrap gap-2">
            <select
              className="rounded-xl border border-white/20 bg-black/40 px-3 py-2 text-sm outline-none hover:border-white/30"
              onChange={(e) => applyTemplate(e.target.value)}
              defaultValue=""
            >
              <option value="">Apply template...</option>
              {templates.map((t) => (
                <option key={t.templateId} value={t.templateId}>
                  {t.name}
                </option>
              ))}
            </select>
            <input
              className="rounded-xl border border-white/20 bg-black/40 px-3 py-2 text-sm outline-none hover:border-white/30"
              placeholder="Template name"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
            />
            <button className="rounded-xl border border-cyan-300/30 bg-cyan-500/15 px-3 py-2 text-sm font-bold text-cyan-200 hover:bg-cyan-500/25" onClick={saveTemplate}>
              Save as Template
            </button>
          </div>
          <div className="flex gap-2">
            <button className="rounded-xl border border-amber-300/30 bg-amber-500/15 px-3 py-2 text-sm font-bold text-amber-200 hover:bg-amber-500/25" onClick={validateRemote}>
              Validate
            </button>
            <button className="rounded-xl border border-emerald-300/30 bg-emerald-500/20 px-3 py-2 text-sm font-bold text-emerald-100 hover:bg-emerald-500/30" onClick={save}>
              <Save size={14} className="mr-1 inline" />
              Save Mapping
            </button>
          </div>
        </div>

        <div className="max-h-[58vh] overflow-auto px-6 pb-4">
          <table className="w-full border-separate border-spacing-y-2 text-sm">
            <thead>
              <tr className="text-left text-white/60">
                <th className="px-3 py-2">Signal</th>
                <th className="px-3 py-2">Device</th>
                <th className="px-3 py-2">Module</th>
                <th className="px-3 py-2">Direction</th>
                <th className="px-3 py-2">Channel</th>
                <th className="px-3 py-2">Invert</th>
              </tr>
            </thead>
            <tbody>
              {SIGNALS.map((signal) => {
                const ref = draft.bindings[signal];
                const conflict = localConflicts.has(`${ref.device}:${ref.moduleType}:${ref.channel}`);
                return (
                  <tr key={signal} className={`rounded-2xl border ${conflict ? "border-red-400/40 bg-red-500/10" : "border-white/10 bg-white/[0.03]"}`}>
                    <td className="rounded-l-2xl px-3 py-2 font-bold tracking-wide text-white/90">{signal}</td>
                    <td className="px-3 py-2">
                      <input
                        className="w-28 rounded-lg border border-white/20 bg-black/40 p-1.5 outline-none focus:border-cyan-300/60"
                        value={ref.device}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            bindings: { ...prev.bindings, [signal]: { ...prev.bindings[signal], device: e.target.value } },
                          }))
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="rounded-lg border border-white/20 bg-black/40 p-1.5 outline-none focus:border-cyan-300/60"
                        value={ref.moduleType}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            bindings: { ...prev.bindings, [signal]: { ...prev.bindings[signal], moduleType: e.target.value as typeof ref.moduleType } },
                          }))
                        }
                      >
                        <option value="DO">DO</option>
                        <option value="DI">DI</option>
                        <option value="AI">AI</option>
                        <option value="AO">AO</option>
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="rounded-lg border border-white/20 bg-black/40 p-1.5 outline-none focus:border-cyan-300/60"
                        value={ref.direction}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            bindings: { ...prev.bindings, [signal]: { ...prev.bindings[signal], direction: e.target.value as typeof ref.direction } },
                          }))
                        }
                      >
                        <option value="OUT">OUT</option>
                        <option value="IN">IN</option>
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        className="rounded-lg border border-white/20 bg-black/40 p-1.5 outline-none focus:border-cyan-300/60"
                        value={ref.channel}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            bindings: { ...prev.bindings, [signal]: { ...prev.bindings[signal], channel: Number(e.target.value) } },
                          }))
                        }
                      >
                        {channelOptions.map((opt) => (
                          <option key={`${opt.moduleType}-${opt.direction}-${opt.channel}`} value={opt.channel}>
                            {opt.channel} ({opt.moduleType}/{opt.direction})
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="rounded-r-2xl px-3 py-2">
                      <input
                        type="checkbox"
                        checked={ref.invert}
                        onChange={(e) =>
                          setDraft((prev) => ({
                            ...prev,
                            bindings: { ...prev.bindings, [signal]: { ...prev.bindings[signal], invert: e.target.checked } },
                          }))
                        }
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="border-t border-white/10 px-6 py-4">
          {errorMessage ? <div className="mb-2 text-sm text-rose-300">Error: {errorMessage}</div> : null}
          {validation ? (
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-sm">
              <div className="mb-1 font-bold text-white">
                {validation.valid ? (
                  <span className="text-emerald-300">
                    <CheckCircle2 size={14} className="mr-1 inline" />
                    Validation passed
                  </span>
                ) : (
                  <span className="text-red-300">
                    <ShieldAlert size={14} className="mr-1 inline" />
                    Validation failed
                  </span>
                )}
              </div>
              {validation.issues.map((issue, i) => (
                <div key={i} className={issue.level === "error" ? "text-red-300" : "text-amber-300"}>
                  [{issue.level}] {issue.message}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-white/45">Run validate before save to check direction and channel conflicts.</div>
          )}
        </div>
      </div>
    </div>
  );
}

