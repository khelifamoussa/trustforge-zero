import {LlmAgent, InMemoryRunner} from '@google/adk';

export const MODEL = process.env.TRUSTFORGE_MODEL || 'gemini-3.5-flash';

export const rootAgent = new LlmAgent({
  name: 'trustforge_governor',
  model: MODEL,
  description: 'TRUSTFORGE ZERO autonomous security certification governor.',
  instruction: `You are the TRUSTFORGE ZERO Governor. Analyze only defensive, synthetic agent-security evidence. Coordinate these specialist responsibilities: Sentinel boundary discovery, Identity Guard least privilege, Tool Guardian integrity, Red Swarm defensive adversarial testing, Forensic root-cause diagnosis, Defense remediation, Memory Guard provenance, Provenance attestation, and Judge certification. Never certify a claim without executed evidence. Never approve a high-risk real-world action without human approval. Return a concise evidence-grounded security assessment.`
});

export async function runLiveAdkProbe(prompt: string) {
  const runner = new InMemoryRunner({agent: rootAgent, appName: 'trustforge_zero'});
  const authors = new Set<string>();
  let finalText = '';
  let events = 0;
  for await (const event of runner.runEphemeral({
    userId: 'trustforge-demo',
    newMessage: {role: 'user', parts: [{text: prompt}]}
  })) {
    events += 1;
    const author = (event as any).author;
    if (author) authors.add(author);
    const parts = (event as any).content?.parts || [];
    for (const part of parts) if (part?.text) finalText += part.text;
  }
  return {
    app_name: 'trustforge_zero',
    model: MODEL,
    events,
    authors_seen: [...authors],
    final_text: finalText.trim(),
    live_model_called: true,
    adk_runtime: '@google/adk'
  };
}
