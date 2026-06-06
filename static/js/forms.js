// ─── TRANSACTION FORM ─────────────────────────────────────────
document.getElementById('form-transaction').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  const data = {
    fromAccountId: form.fromAccountId.value.trim(),
    toAccountId:   form.toAccountId.value.trim(),
    amount:        Number(form.amount.value),
    currency:      form.currency.value,
    channel:       form.channel.value,
    merchantId:    form.merchantId.value.trim() || null,
    country:       form.country.value.toUpperCase().trim() || 'IN',
    description:   form.description.value.trim() || null,
  };

  const errors = {};
  if (!data.fromAccountId)                          errors.fromAccountId = 'Required';
  if (!data.toAccountId)                            errors.toAccountId   = 'Required';
  if (!data.amount || isNaN(data.amount) || data.amount <= 0) errors.amount = 'Must be a positive number';
  if (!data.channel)                                errors.channel       = 'Required';

  if (Object.keys(errors).length) { showFieldErrors('transaction', errors); return; }
  clearFieldErrors('transaction');
  setButtonLoading('btn-transaction', true);

  try {
    const res  = await fetch('/api/events/transaction', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(extractError(result));
    showResult('transaction', result, true);
    onEventSent({ type: 'TRANSACTION', data, result });
    setTimeout(() => {
      const box = document.getElementById('result-transaction');
      if (box && box.className.includes('result-box-success')) box.classList.add('hidden');
    }, 4000);
  } catch (err) {
    showResult('transaction', { error: err.message }, false);
  } finally {
    setButtonLoading('btn-transaction', false, '⚡ Send Transaction Event');
  }
});

// ─── CUSTOMER FORM ────────────────────────────────────────────
document.getElementById('form-customer').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  const data = {
    fullName:     form.fullName.value.trim(),
    pan:          form.pan.value.toUpperCase().trim(),
    dob:          form.dob.value,
    address:      form.address.value.trim(),
    mobile:       form.mobile.value.trim(),
    email:        form.email.value.trim(),
    kycRiskScore: Number(form.kycRiskScore.value),
  };

  const errors = {};
  if (!data.fullName)                                    errors.fullName = 'Required';
  if (!/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(data.pan))    errors.pan      = 'Invalid PAN (e.g. ABCDE1234F)';
  if (!data.dob)                                         errors.dob      = 'Required';
  if (!data.address)                                     errors.address  = 'Required';
  if (!/^[6-9]\d{9}$/.test(data.mobile))                errors.mobile   = 'Invalid mobile (10 digits, starts 6-9)';
  if (!data.email.includes('@'))                         errors.email    = 'Invalid email';

  if (Object.keys(errors).length) { showFieldErrors('customer', errors); return; }
  clearFieldErrors('customer');
  setButtonLoading('btn-customer', true);

  try {
    const res    = await fetch('/api/events/customer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(extractError(result));
    showResult('customer', result, true);
    onEventSent({ type: 'CUSTOMER', data, result });
    setTimeout(() => {
      const box = document.getElementById('result-customer');
      if (box && box.className.includes('result-box-success')) box.classList.add('hidden');
    }, 4000);
  } catch (err) {
    showResult('customer', { error: err.message }, false);
  } finally {
    setButtonLoading('btn-customer', false, '👤 Register Customer');
  }
});

// ─── ACCOUNT FORM ─────────────────────────────────────────────
document.getElementById('form-account').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  const data = {
    customerId:     form.customerId.value.trim(),
    accountType:    form.accountType.value,
    currentBalance: Number(form.currentBalance.value) || 0,
    currency:       form.currency.value,
    branch:         form.branch.value.trim(),
    ifscCode:       form.ifscCode.value.toUpperCase().trim(),
  };

  const errors = {};
  if (!data.customerId)                                   errors.customerId = 'Required';
  if (!data.branch)                                       errors.branch     = 'Required';
  if (!/^[A-Z]{4}0[A-Z0-9]{6}$/.test(data.ifscCode))    errors.ifscCode   = 'Invalid IFSC (e.g. HDFC0001234)';

  if (Object.keys(errors).length) { showFieldErrors('account', errors); return; }
  clearFieldErrors('account');
  setButtonLoading('btn-account', true);

  try {
    const res    = await fetch('/api/events/account', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(extractError(result));
    showResult('account', result, true);
    onEventSent({ type: 'ACCOUNT', data, result });
    setTimeout(() => {
      const box = document.getElementById('result-account');
      if (box && box.className.includes('result-box-success')) box.classList.add('hidden');
    }, 4000);
  } catch (err) {
    showResult('account', { error: err.message }, false);
  } finally {
    setButtonLoading('btn-account', false, '🏦 Register Account');
  }
});

// ─── MERCHANT FORM ────────────────────────────────────────────
document.getElementById('form-merchant').addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;

  const data = {
    name:         form.name.value.trim(),
    mcc:          form.mcc.value.trim(),
    country:      form.country.value.toUpperCase().trim() || 'IN',
    riskCategory: form.riskCategory.value,
    gstin:        form.gstin.value.toUpperCase().trim() || null,
  };

  const errors = {};
  if (!data.name) errors.name = 'Required';
  if (!data.mcc)  errors.mcc  = 'Required (e.g. 6011, 7011)';

  if (Object.keys(errors).length) { showFieldErrors('merchant', errors); return; }
  clearFieldErrors('merchant');
  setButtonLoading('btn-merchant', true);

  try {
    const res    = await fetch('/api/events/merchant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(extractError(result));
    showResult('merchant', result, true);
    onEventSent({ type: 'MERCHANT', data, result });
    setTimeout(() => {
      const box = document.getElementById('result-merchant');
      if (box && box.className.includes('result-box-success')) box.classList.add('hidden');
    }, 4000);
  } catch (err) {
    showResult('merchant', { error: err.message }, false);
  } finally {
    setButtonLoading('btn-merchant', false, '🏪 Register Merchant');
  }
});

// ─── Error extraction helper ──────────────────────────────────
function extractError(result) {
  if (typeof result.detail === 'string') return result.detail;
  if (Array.isArray(result.detail)) {
    return result.detail.map(d => `${d.loc?.slice(-1)[0] ?? ''}: ${d.msg}`).join('; ');
  }
  return result.error || result.message || 'Request failed';
}
