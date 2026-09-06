package com.agentfusion.core;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
public class TaskRuntimeTest {
 static Set<String> set(String... s) { return new HashSet<>(Arrays.asList(s)); }
 static TaskRuntime rt() { return new TaskRuntime(3, (id,state,detail)->{}); }
 static TaskRuntime.Step step(String id,Set<String>d,Set<String>r,TaskRuntime.Action a){return new TaskRuntime.Step(id,d,r,a);}
 static void check(boolean ok,String name){if(!ok)throw new AssertionError(name);System.out.println("PASS "+name);}
 public static void main(String[] args)throws Exception{
  AtomicInteger n=new AtomicInteger();
  Map<String,TaskRuntime.State> result=rt().run(Arrays.asList(
   step("a",set(),set(),c->n.incrementAndGet()),
   step("b",set("a"),set(),c->{if(n.get()!=1)throw new Exception();n.incrementAndGet();})));
  check(n.get()==2 && result.get("b")==TaskRuntime.State.SUCCEEDED,"dependency_order");
  AtomicInteger active=new AtomicInteger(),max=new AtomicInteger();
  TaskRuntime.Action screen=c->{int a=active.incrementAndGet();max.accumulateAndGet(a,Math::max);try{Thread.sleep(30);}finally{active.decrementAndGet();}};
  rt().run(Arrays.asList(step("s1",set(),set("screen"),screen),step("s2",set(),set("screen"),screen)));
  check(max.get()==1,"screen_mutual_exclusion");
  CountDownLatch both=new CountDownLatch(2);
  TaskRuntime.Action parallel=c->{both.countDown();if(!both.await(2,TimeUnit.SECONDS))throw new Exception("Not parallel");};
  result=rt().run(Arrays.asList(step("p1",set(),set("file:a"),parallel),step("p2",set(),set("file:b"),parallel)));
  check(result.values().stream().allMatch(s->s==TaskRuntime.State.SUCCEEDED),"independent_parallelism");
  AtomicBoolean ran=new AtomicBoolean();
  result=rt().run(Arrays.asList(step("fail",set(),set(),c->{throw new Exception();}),step("child",set("fail"),set(),c->ran.set(true))));
  check(!ran.get()&&result.get("child")==TaskRuntime.State.BLOCKED,"failure_blocks_dependents");
  boolean rejected=false;try{rt().run(Arrays.asList(step("a",set("b"),set(),c->{}),step("b",set("a"),set(),c->{})));}catch(IllegalArgumentException e){rejected=true;}
  check(rejected,"cycle_rejected");
  rejected=false;try{rt().run(Arrays.asList(step("a",set("missing"),set(),c->{})));}catch(IllegalArgumentException e){rejected=true;}
  check(rejected,"missing_dependency_rejected");
  TaskRuntime stopped=rt();stopped.cancel();
  result=stopped.run(Arrays.asList(step("never",set(),set(),c->ran.set(true))));
  check(!ran.get()&&result.get("never")==TaskRuntime.State.CANCELLED,"cancel_before_start");
  TaskRuntime cooperative=rt();CountDownLatch started=new CountDownLatch(1);
  ExecutorService executor=Executors.newSingleThreadExecutor();
  try{
   Future<Map<String,TaskRuntime.State>> f=executor.submit(()->cooperative.run(Arrays.asList(step("loop",set(),set(),c->{started.countDown();while(true){c.checkCancelled();Thread.sleep(5);}}))));
   if(!started.await(2,TimeUnit.SECONDS))throw new AssertionError("start timeout");cooperative.cancel();
   check(f.get(2,TimeUnit.SECONDS).get("loop")==TaskRuntime.State.CANCELLED,"cooperative_cancel_running");
  }finally{executor.shutdownNow();}
  System.out.println("8 tests passed. JVM-only tests; Android integration not tested.");
 }
}