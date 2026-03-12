# 🌐 Namecheap DNS Setup for ShandorCode

## 📋 Quick Steps

### 1. Login to Namecheap
Go to: https://www.namecheap.com/myaccount/login/

### 2. Find Your Domain
1. Click **Domain List** in the left sidebar
2. Find **gozerai.com**
3. Click **Manage** button next to it

### 3. Navigate to DNS Settings
1. Look for the **Advanced DNS** tab (or **DNS** tab)
2. Click it

### 4. Add A Record
You should see a section called **HOST RECORDS** or **DNS Records**

**Add New Record:**
- **Type**: `A Record`
- **Host**: `shandor` (NOT shandor.gozerai.com, just shandor)
- **Value**: `72.61.76.32`
- **TTL**: `Automatic` (or `3600` if you need to choose)

Click **Save All Changes** or green checkmark ✅

---

## 📸 Visual Guide

### What You'll See in Namecheap:

```
┌─────────────────────────────────────────────────────┐
│ HOST RECORDS                                        │
├─────────┬──────────┬────────────────┬──────┬───────┤
│  Type   │   Host   │     Value      │ TTL  │       │
├─────────┼──────────┼────────────────┼──────┼───────┤
│ A Record│  shandor │  72.61.76.32   │ Auto │   ✓   │
│         │          │                │      │       │
└─────────┴──────────┴────────────────┴──────┴───────┘
                      ▲
                Add New Record
```

### Important Notes:

**✅ CORRECT - Host field:**
```
shandor
```

**❌ WRONG - Don't include full domain:**
```
shandor.gozerai.com  ← NO!
```

Namecheap automatically appends `.gozerai.com` to whatever you put in the Host field.

---

## 🔍 Common Namecheap Scenarios

### Scenario 1: Fresh Domain (No Records Yet)
- You'll see an empty table or default records
- Just click "Add New Record"
- Fill in the details above
- Save

### Scenario 2: Existing Records
- You might see some default records (like @ pointing to parking page)
- That's fine! Leave them
- Just add the new A record for `shandor`
- Save

### Scenario 3: Using Namecheap Nameservers
If you see something like:
```
Nameservers: BasicDNS
or
Nameservers: dns1.registrar-servers.com
```
**This is perfect!** Just add the A record.

### Scenario 4: Using Custom Nameservers
If nameservers point somewhere else (like Cloudflare), you'll need to add the DNS record there instead.

---

## ⚡ Step-by-Step Screenshots Guide

### Step 1: Domain List
```
Dashboard → Domain List → Find gozerai.com → Click "Manage"
```

### Step 2: Advanced DNS
```
Tabs at top: [Details] [Products] [Advanced DNS] ← Click this
```

### Step 3: Add Record
```
Scroll to "HOST RECORDS" section
Click "+ ADD NEW RECORD" button
```

### Step 4: Fill Details
```
Dropdown: Select "A Record"
Host: Type "shandor"
Value: Type "72.61.76.32"
TTL: Leave as "Automatic"
```

### Step 5: Save
```
Click green checkmark ✓
OR
Click "Save All Changes" button
```

---

## ✅ Verification

### Immediately After Saving:
Namecheap will show your new record in the table:
```
Type: A Record
Host: shandor
Value: 72.61.76.32
TTL: Automatic
```

### Test DNS (Wait 5-10 minutes):

**From Windows PowerShell:**
```powershell
nslookup shandor.gozerai.com
```

**Should return:**
```
Name:    shandor.gozerai.com
Address: 72.61.76.32
```

**Or use online tool:**
- Go to: https://dnschecker.org/
- Enter: `shandor.gozerai.com`
- Should show `72.61.76.32` across all servers

---

## ⏱️ DNS Propagation Time

**Namecheap DNS is usually fast:**
- **Minimum**: 5 minutes
- **Typical**: 10-30 minutes
- **Maximum**: 48 hours (rare)

**While waiting**, you can continue with VPS setup!

---

## 🔧 Troubleshooting

### Issue: Can't find "Manage" button
**Solution**: Make sure you're looking at the right domain list. Try:
- Dashboard → Domain List
- Or direct link: https://ap.www.namecheap.com/domains/list/

### Issue: Can't find "Advanced DNS" tab
**Solution**: 
- Some accounts call it just "DNS"
- Or "DNS Management"
- Should be one of the tabs after clicking domain

### Issue: "Host" field not accepting "shandor"
**Solution**: 
- Make sure you're adding an "A Record" not something else
- Try typing it exactly: `shandor` (lowercase, no dots)

### Issue: DNS not resolving after 1 hour
**Solution**:
1. Check if you saved the changes (green checkmark)
2. Verify nameservers are Namecheap's (not external)
3. Clear your local DNS cache:
   ```powershell
   ipconfig /flushdns
   ```
4. Try from different device/network

---

## 🎯 What Happens After DNS Setup

Once DNS is configured:

1. **5-10 minutes**: DNS starts propagating
2. **30 minutes**: Fully propagated globally
3. **Deploy ShandorCode**: VPS will recognize the domain
4. **Let's Encrypt**: Caddy will automatically get SSL certificate
5. **Live!**: https://shandor.gozerai.com works

---

## 📋 Quick Checklist

- [ ] Login to Namecheap
- [ ] Find gozerai.com in Domain List
- [ ] Click Manage
- [ ] Go to Advanced DNS tab
- [ ] Add A Record:
  - Host: `shandor`
  - Value: `72.61.76.32`
- [ ] Save changes
- [ ] Wait 5-10 minutes
- [ ] Test with `nslookup shandor.gozerai.com`
- [ ] Proceed with VPS deployment

---

## 🚀 Ready for Next Step?

Once you see the DNS resolving (even if still propagating), you can:

1. Start your Hostinger VPS
2. Run the deployment
3. Let's Encrypt will handle SSL automatically

**The deployment will work even if DNS is still propagating!**

---

## 💡 Pro Tips

1. **Do DNS first**: Set it up now, even before VPS setup
2. **Use TTL Auto**: Namecheap handles it optimally
3. **Keep it simple**: Just the one A record for now
4. **Test multiple ways**: Use both `nslookup` and online checkers
5. **Don't panic**: DNS can take time, that's normal

---

## 📞 Need Help?

**If you get stuck:**
1. Take a screenshot of your Namecheap DNS page
2. Let me know what you see
3. I'll guide you through it

**Common Namecheap Support:**
- Namecheap Live Chat (usually fast)
- https://www.namecheap.com/support/

---

**Ready to set up DNS?** Let me know when you've added the record! 🌐
