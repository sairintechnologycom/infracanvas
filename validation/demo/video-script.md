# InfraCanvas Demo Video Script

**Duration:** 2–3 minutes  
**Format:** Silent video with text callouts — no narration, no voice-over (D-03)  
**Optimised for:** Mute autoplay on LinkedIn and Reddit scroll  
**Recording tool:** OBS Studio (recording) + DaVinci Resolve (editing + text callouts)  
**Alternative:** ScreenFlow ($149) for single-tool macOS workflow

---

## Pre-Recording Setup

Before recording, load the viewer with curated sample data:

1. Use `viewer/src/sample-data.ts` as the base dataset — enhance if needed to show:
   - At least 15 resources across 2+ VPCs
   - Mixed severity findings (at least one Critical, two High, several Medium)
   - At least 3 different resource types (EC2, RDS, S3, security groups, etc.)
   - Cost estimates on at least 5 resources
   - One drift change (planned addition or modification)

2. Export the viewer with sample data: `infracanvas export --data viewer/src/sample-data.ts`

3. Set terminal to a clean state: dark theme, 14pt font, no distracting open windows.

4. Prepare these commands to be typed during recording:
   - `cd ~/demo-terraform/`
   - `infracanvas scan ./terraform`

5. Have the exported HTML file ready to open in Chrome after the terminal sequence.

---

## Scene Sequence

### Scene 1 — The Problem (0:00–0:15)

**Visual:** Screenshot of a cluttered desktop or browser showing 5 tabs: AWS Console, Terraform terminal, tfsec output, Infracost table, draw.io diagram

**Text overlay:** "5 tabs open. 0 clarity."

**Transition:** Brief pause (1 second), then cut to terminal

**Production note:** This can be a static screenshot with the text overlay added in DaVinci Resolve. No live recording needed for this scene.

---

### Scene 2 — One Command (0:15–0:30)

**Visual:** Clean terminal window (dark theme)

**Text overlay:** "What if one command showed you everything?"

**Action:** Type and execute: `$ infracanvas scan ./terraform`

**Production note:** Type slowly and deliberately. The command should be legible. Use a terminal font that's readable at the exported video resolution (minimum 1080p).

---

### Scene 3 — Terminal Progress (0:30–0:45)

**Visual:** Terminal showing real `infracanvas scan` output — file parsing progress, resource count, finding count

**Text overlay:** (none — let the terminal output speak for itself)

**Action:** Show the scan completing. The terminal output should show something like:
```
Parsing ./terraform... 18 resources found
Building resource graph... done
Running security checks... 7 findings (1 critical, 3 high, 3 medium)
Estimating costs... $847/month
Exporting HTML... done
Opening viewer in browser...
```

**Production note:** Use real CLI output from a scan on the sample data. Do not fake the terminal. The authenticity of seeing a real tool run is part of the demo's credibility.

---

### Scene 4 — Interactive Diagram (0:45–1:30)

**Visual:** Browser opens with the ReactFlow viewer showing the curated sample data

**Text overlay sequence (stagger with brief pauses between):**
- "Your entire infrastructure. One diagram." (at 0:45)
- "VPC grouping. Dependency edges." (at 1:00)
- "Security findings. Per resource." (at 1:10)

**Action:** 
1. Let the diagram settle on screen (2 seconds)
2. Slowly pan/zoom to show the VPC groupings and resource nodes
3. Hover over a resource with a critical finding — let the finding badge be visible

**Production note:** The viewer already renders VPC/subnet groupings, resource icons, dependency edges, and security finding badges. Use the real viewer — do not mock this. Slow, deliberate movement. Frantic clicking looks unpolished.

---

### Scene 5 — Finding Detail (1:30–2:00)

**Visual:** Click on a resource node with a security finding. The detail panel opens on the right.

**Text overlay:** "Security findings with remediation. No config required."

**Action:** 
1. Click on a resource with a Critical or High severity finding
2. Let the detail panel animate open
3. Scroll slightly in the detail panel to show the remediation guidance

**Design overlay note (per D-02):** If the detail panel in the current viewer is not yet polished to the demo standard, add a design overlay in DaVinci Resolve showing the intended final UI — clean severity badge, finding title, description, remediation steps. Label it clearly as the final product direction in the overlay styling.

---

### Scene 6 — Score Card (2:00–2:30)

**Visual:** Navigate to the score card view (or cut to a design overlay of the score card)

**Text overlay:** "Your infrastructure gets a letter grade. Share it with your team."

**Design overlay note (per D-02):** The score card polish is aspirational. Use a design overlay here showing the intended score card: letter grade (e.g., "B+"), category breakdown (Security: A, Cost: B, Compliance: C+), summary of findings by severity. The overlay should look like a realistic product screenshot, not a wireframe. DaVinci Resolve text/shape tools are sufficient for this.

---

### Scene 7 — End Screen (2:30–2:45)

**Visual:** Fade to dark or clean solid background

**Text overlay (large, centered):**

```
infracanvas.dev

One command. Your entire infrastructure.
```

**Secondary text (smaller, below):**

```
Early access open now
```

**Production note:** Hold the end screen for 3–4 seconds. No audio, no animation — clean and deliberate.

---

## Text Callout Style Guide

Use consistent text callout styling throughout the video (add in DaVinci Resolve):

- **Font:** Inter or SF Pro Display (clean, technical)
- **Color:** White text on semi-transparent dark background (#1a1a1a at 85% opacity)
- **Size:** Large enough to read on mobile without zooming (minimum 28pt at 1080p)
- **Position:** Lower third for most callouts; centered for Scene 1 and end screen
- **Duration:** 2–4 seconds per callout, fade in/out (0.2s transitions)
- **Pacing:** Let callouts breathe — do not stack them. One callout visible at a time.

---

## Recording Checklist

- [ ] OBS Studio installed and configured (or ScreenFlow if using alternative)
- [ ] Terminal set to dark theme, 14pt font, clean state
- [ ] `viewer/src/sample-data.ts` enhanced to show 15+ resources, mixed severity findings
- [ ] Sample data scan has been run and HTML export is ready
- [ ] Chrome browser ready to open the HTML file at the right moment
- [ ] Text callouts designed and queued in DaVinci Resolve before final render
- [ ] Design overlays for Scenes 5 and 6 prepared (D-02: aspirational polish)
- [ ] Video exported at 1080p minimum, MP4 format
- [ ] Video tested for mute autoplay compatibility (no audio dependency)
- [ ] Total runtime 2:00–2:45 (trim ruthlessly if longer)
- [ ] End screen includes infracanvas.dev URL as text (not a clickable link in video)

---

## Upload Notes

- **LinkedIn:** Upload MP4 directly to LinkedIn post (do not link to YouTube). LinkedIn autoplays natively.
- **Reddit:** Reddit supports MP4 uploads natively; alternatively link to Loom free tier or YouTube unlisted for embed support.
- **Landing page (infracanvas.dev):** Host via Loom free tier or YouTube unlisted for clean embed. Do not self-host the MP4 (bandwidth cost and no CDN).
