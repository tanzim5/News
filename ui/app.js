const generateBtn = document.getElementById('generateBtn');
const headlinesEl = document.getElementById('headlines');
const minHeadlinesEl = document.getElementById('minHeadlines');
const maxHeadlinesEl = document.getElementById('maxHeadlines');
const targetMinEl = document.getElementById('targetMin');
const targetMaxEl = document.getElementById('targetMax');
const generateAudioEl = document.getElementById('generateAudio');
const apiKeyEl = document.getElementById('apiKey');
const scriptOutputEl = document.getElementById('scriptOutput');
const statusEl = document.getElementById('status');
const metaEl = document.getElementById('meta');
const audioLink = document.getElementById('audioLink');

headlinesEl.value = `অর্থনীতিতে মূল্যস্ফীতি কমাতে নতুন নীতিমালা ঘোষণা
রাজধানীতে গণপরিবহন ব্যবস্থায় নতুন রুট চালু
বিদ্যালয় শিক্ষার্থীদের জন্য ডিজিটাল লার্নিং প্ল্যাটফর্ম সম্প্রসারণ
জ্বালানি সাশ্রয়ে শিল্পখাতে দক্ষতা বৃদ্ধি কর্মসূচি শুরু
উপকূলীয় এলাকায় ঘূর্ণিঝড় প্রস্তুতি মহড়া সম্পন্ন
চিকিৎসা সেবায় জেলা হাসপাতালে নতুন বিশেষজ্ঞ ইউনিট`;

generateBtn.addEventListener('click', async () => {
  const headlines = headlinesEl.value.trim();
  if (!headlines) {
    statusEl.textContent = 'Please enter at least one headline.';
    return;
  }

  scriptOutputEl.textContent = 'Generating...';
  statusEl.textContent = 'Working...';
  metaEl.textContent = '';
  audioLink.classList.add('hidden');
  audioLink.removeAttribute('href');

  const payload = {
    headlines,
    min_headlines: Number(minHeadlinesEl.value || 6),
    max_headlines: Number(maxHeadlinesEl.value || 14),
    target_seconds_min: Number(targetMinEl.value || 60),
    target_seconds_max: Number(targetMaxEl.value || 90),
    generate_audio: generateAudioEl.checked,
    sarvam_api_key: apiKeyEl.value.trim(),
  };

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      scriptOutputEl.textContent = data.error || 'Failed to generate output.';
      statusEl.textContent = 'Request failed.';
      return;
    }

    scriptOutputEl.textContent = data.script || '';
    metaEl.textContent = `Duration ~${data.duration_seconds.toFixed(1)}s (${data.duration_minutes.toFixed(2)} min) • Headlines used: ${data.headlines_used}`;
    statusEl.textContent = data.message || 'Done.';

    if (data.audio_url) {
      audioLink.href = data.audio_url;
      audioLink.classList.remove('hidden');
    }
  } catch (error) {
    scriptOutputEl.textContent = `Unexpected error: ${String(error)}`;
    statusEl.textContent = 'Failed due to network/server error.';
  }
});
