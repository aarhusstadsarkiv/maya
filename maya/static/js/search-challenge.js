/* No network requests or search work until the local proof is ready. */
(async () => {
    const status = document.getElementById('status');
    const form = document.getElementById('challenge');
    const started = performance.now();
    try {
        if (!crypto.subtle) throw new Error('Secure browser required');
        const encoder = new TextEncoder();
        const prefix = '0'.repeat(Number(document.getElementById('difficulty').value));
        const token = form.elements.token.value;
        for (let solution = 0; ; solution++) {
            const buffer = await crypto.subtle.digest('SHA-256', encoder.encode(`${token}:${solution}`));
            const digest = Array.from(new Uint8Array(buffer), byte => byte.toString(16).padStart(2, '0')).join('');
            if (digest.startsWith(prefix)) {
                form.elements.solution.value = String(solution);
                break;
            }
            if (performance.now() - started > 60000) throw new Error('Verification timed out');
            if (solution % 128 === 0) await new Promise(resolve => setTimeout(resolve, 0));
        }
        const remaining = Number(document.getElementById('wait').value) - (performance.now() - started);
        if (remaining > 0) await new Promise(resolve => setTimeout(resolve, remaining));
        status.textContent = 'Continuing to search…';
        form.submit();
    } catch (error) {
        status.textContent = 'Unable to verify this browser. Enable JavaScript and cookies, use HTTPS, and reload to try again.';
    }
})();
