import numpy as np
import matplotlib.pyplot as plt

# Categories (x-axis)
labels = [
    "Stages", "PHV", "Gateway", "HashUnits", "MAP RAM",
    "Meter ALUs", "SRAM", "TCAM", "VLIW", "Logical Table\nIds"
]

# Approximated values from the image (percent)
active_rmt = [100, 77, 16, 72, 90, 44, 74, 83, 78, 36]
p4runpro   = [100, 30, 14, 92, 65, 46, 44, 94, 100, 15]
stagerun   = [100, 74, 21, 81, 53, 40, 54, 55, 85, 75]

x = np.arange(len(labels))
w = 0.25  # bar width

fig, ax = plt.subplots(figsize=(14, 7))

ax.bar(x - w, active_rmt, width=w, color="#d9d9d9", label="ActiveRMT")
ax.bar(x,     p4runpro,   width=w, color="#73ad21", label="P4RunPro")
ax.bar(x + w, stagerun,   width=w, color="#a40000", label="StageRun")

ax.set_ylabel("Usage (%)", fontsize=26)
ax.set_ylim(0, 110)

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=35, ha="center", fontsize=24)
ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=24)
ax.grid(axis="y", linestyle=":", linewidth=1, alpha=0.5)

leg = ax.legend(loc="upper center", bbox_to_anchor=(0.57, 1.03),
                frameon=True, fontsize=22)
leg.get_frame().set_alpha(0.95)

plt.tight_layout()
plt.savefig("frameworks_resource_comparison_v4.pdf", bbox_inches="tight")
#plt.savefig("resource_usage.png", dpi=300, bbox_inches="tight")
#plt.show()