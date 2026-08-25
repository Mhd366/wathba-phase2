"use client";

import { FormEvent, useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

type Role = "coach" | "athlete";
type Mode = "signin" | "signup" | "forgot" | "reset" | "pending" | "check-email";

export function AuthScreen({onAuthenticated}:{onAuthenticated:(profile:{role:Role;fullName:string})=>void}) {
  const [mode,setMode]=useState<Mode>("signin");
  const [email,setEmail]=useState("");
  const [password,setPassword]=useState("");
  const [confirmPassword,setConfirmPassword]=useState("");
  const [fullName,setFullName]=useState("");
  const [requestedRole,setRequestedRole]=useState<Role>("athlete");
  const [showPassword,setShowPassword]=useState(false);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  const resolveAccess=async(userId:string)=>{
    const {data:profile,error:profileError}=await supabase.from("profiles").select("full_name,role").eq("id",userId).maybeSingle();
    if(profileError) throw profileError;
    if(profile?.role==="coach"||profile?.role==="athlete"){
      onAuthenticated({role:profile.role,fullName:profile.full_name});
      return;
    }
    const {data:request,error:requestError}=await supabase.from("registration_requests").select("status,requested_role").eq("user_id",userId).maybeSingle();
    if(requestError) throw requestError;
    if(request?.status==="rejected"){
      await supabase.auth.signOut();
      setError("This registration was not approved. Contact the federation administrator.");
      setMode("signin");
      return;
    }
    setNotice(request?.requested_role==="coach"?"Your coach account is awaiting federation approval.":"Your athlete account is awaiting assignment to a coach.");
    setMode("pending");
  };

  useEffect(()=>{
    let active=true;
    supabase.auth.getSession().then(async({data})=>{
      if(!active)return;
      try{if(data.session)await resolveAccess(data.session.user.id)}catch(e){setError(e instanceof Error?e.message:"Unable to verify account access.")}finally{setLoading(false)}
    });
    const {data:{subscription}}=supabase.auth.onAuthStateChange((event)=>{
      if(event==="PASSWORD_RECOVERY")setMode("reset");
    });
    return()=>{active=false;subscription.unsubscribe()};
  },[]);

  const submit=async(event:FormEvent)=>{
    event.preventDefault();setError("");setNotice("");setLoading(true);
    try{
      if(mode==="signin"){
        const {data,error}=await supabase.auth.signInWithPassword({email,password});
        if(error)throw error;
        if(data.user)await resolveAccess(data.user.id);
      }else if(mode==="signup"){
        if(fullName.trim().length<3)throw new Error("Enter your full name.");
        if(password.length<8)throw new Error("Password must contain at least 8 characters.");
        if(password!==confirmPassword)throw new Error("Passwords do not match.");
        const {data,error}=await supabase.auth.signUp({email,password,options:{emailRedirectTo:window.location.origin,data:{full_name:fullName.trim(),requested_role:requestedRole}}});
        if(error)throw error;
        if(data.session&&data.user)await resolveAccess(data.user.id);else setMode("check-email");
      }else if(mode==="forgot"){
        const {error}=await supabase.auth.resetPasswordForEmail(email,{redirectTo:window.location.origin});
        if(error)throw error;
        setNotice("Password recovery instructions were sent to your email.");
      }else if(mode==="reset"){
        if(password.length<8)throw new Error("Password must contain at least 8 characters.");
        if(password!==confirmPassword)throw new Error("Passwords do not match.");
        const {error}=await supabase.auth.updateUser({password});
        if(error)throw error;
        setNotice("Password updated. You can continue to your account.");setMode("signin");
      }
    }catch(e){setError(e instanceof Error?e.message:"Authentication failed.")}finally{setLoading(false)}
  };

  if(loading&&mode==="signin")return <main className="auth-status-page"><div className="auth-loader"/><strong>Securing your WATHBA workspace…</strong></main>;
  if(mode==="pending"||mode==="check-email")return <main className="auth-status-page"><img src="/wathba-logo.jpeg" alt="WATHBA"/><span>{mode==="pending"?"ACCOUNT UNDER REVIEW":"VERIFY YOUR EMAIL"}</span><h1>{mode==="pending"?"Your workspace is being prepared.":"Check your inbox to continue."}</h1><p>{mode==="pending"?notice:"We sent a secure confirmation link to your email. Open it, then return here to sign in."}</p><button onClick={async()=>{await supabase.auth.signOut();setMode("signin");setNotice("")}}>Back to sign in</button></main>;

  return <main className="login-page"><section className="login-brand-panel"><div className="login-logo"><img src="/wathba-logo.jpeg" alt="WATHBA"/></div><div className="login-story"><span>FEDERATION PERFORMANCE INTELLIGENCE</span><h1>Every lane.<br/>Every athlete.<br/>One clear edge.</h1><p>Secure sprint intelligence for coaches and athletes—from race video to measurable development.</p></div><div className="login-track"><i/><i/><i/><i/><i/><i/><i/><i/></div><div className="login-proof"><article><strong>8</strong><span>lane-aware<br/>analysis</span></article><article><strong>3</strong><span>sprint event<br/>modules</span></article><article><strong>1</strong><span>protected athlete<br/>performance file</span></article></div></section><section className="login-form-panel"><form onSubmit={submit}><div className="login-form-head"><span>SECURE FEDERATION ACCESS</span><h2>{mode==="signup"?"Create your account":mode==="forgot"?"Recover access":mode==="reset"?"Set a new password":"Welcome to WATHBA"}</h2><p>{mode==="signup"?"Register as an athlete or request coach access.":mode==="forgot"?"We will send a secure reset link to your email.":mode==="reset"?"Choose a strong password for your account.":"Sign in to your assigned performance workspace."}</p></div>{mode==="signup"&&<><div className="account-tabs"><button type="button" className={requestedRole==="athlete"?"active":""} onClick={()=>setRequestedRole("athlete")}><b>◎</b><span>Athlete<strong>Join your coach</strong></span></button><button type="button" className={requestedRole==="coach"?"active":""} onClick={()=>setRequestedRole("coach")}><b>⌁</b><span>Coach<strong>Approval required</strong></span></button></div><label className="login-field"><span>FULL NAME</span><input required value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Enter your full name"/></label></>}<label className="login-field"><span>EMAIL ADDRESS</span><input type="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="name@example.com"/></label>{mode!=="forgot"&&<label className="login-field"><span>{mode==="reset"?"NEW PASSWORD":"PASSWORD"}</span><div><input required minLength={8} type={showPassword?"text":"password"} value={password} onChange={e=>setPassword(e.target.value)} placeholder="Minimum 8 characters"/><button type="button" onClick={()=>setShowPassword(x=>!x)}>{showPassword?"Hide":"Show"}</button></div></label>}{(mode==="signup"||mode==="reset")&&<label className="login-field"><span>CONFIRM PASSWORD</span><input required minLength={8} type="password" value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)} placeholder="Repeat your password"/></label>}{error&&<p className="auth-error">{error}</p>}{notice&&<p className="auth-success">{notice}</p>}<button className="login-submit" disabled={loading}>{loading?"Please wait…":mode==="signup"?"Create account":mode==="forgot"?"Send recovery email":mode==="reset"?"Update password":"Sign in securely"}<b>→</b></button><div className="auth-mode-actions">{mode==="signin"?<><button type="button" onClick={()=>{setMode("signup");setError("")}}>Create an account</button><button type="button" onClick={()=>{setMode("forgot");setError("")}}>Forgot password?</button></>:<button type="button" onClick={()=>{setMode("signin");setError("");setNotice("")}}>← Back to sign in</button>}</div><p className="login-notice"><i/> Access is assigned from your verified federation profile.</p></form><footer><span>WATHBA PERFORMANCE LAB</span><small>Protected federation environment · Phase 2</small></footer></section></main>;
}
