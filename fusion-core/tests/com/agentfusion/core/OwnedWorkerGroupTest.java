package com.agentfusion.core;
import java.util.concurrent.CountDownLatch;
public final class OwnedWorkerGroupTest {
  static void check(boolean v,String m){if(!v)throw new AssertionError(m);}
  public static void main(String[] a)throws Exception{
    OwnedWorkerGroup g=new OwnedWorkerGroup(); CountDownLatch release=new CountDownLatch(1);
    g.start("stubborn",()->{try{release.await();}catch(InterruptedException ignored){try{release.await();}catch(InterruptedException ignoredAgain){}}});
    g.requestStop(); check(!g.awaitQuiescence(10),"stubborn worker must remain owned");
    release.countDown(); check(g.awaitQuiescence(1000),"worker should eventually stop");
    boolean rejected=false;try{g.start("late",()->{});}catch(IllegalStateException e){rejected=true;}check(rejected,"registration sealed");
    OwnedWorkerGroup empty=new OwnedWorkerGroup();
    check(!empty.isQuiescent(),"open registration is not quiescent");
    rejected=false;try{empty.awaitQuiescence(0);}catch(IllegalStateException e){rejected=true;}
    check(rejected,"await must require sealed registration");
    empty.seal();check(empty.awaitQuiescence(0),"sealed empty group is quiescent");
    rejected=false;try{empty.awaitQuiescence(-1);}catch(IllegalArgumentException e){rejected=true;}
    check(rejected,"negative timeout rejected");
    OwnedWorkerGroup observed=new OwnedWorkerGroup();CountDownLatch done=new CountDownLatch(1);
    observed.start("held",()->{try{done.await();}catch(InterruptedException e){Thread.currentThread().interrupt();}});
    observed.seal();
    try {
      Thread.currentThread().interrupt();
      rejected=false;try{observed.awaitQuiescence(1000);}catch(InterruptedException e){rejected=true;}
      check(rejected,"observer interruption propagated");
      check(!observed.isQuiescent(),"observer interruption must retain ownership");
    } finally {Thread.interrupted();done.countDown();}
    check(observed.awaitQuiescence(1000),"observed worker terminated");
    System.out.println("6 worker lifecycle tests passed (stop, sealed start, open wait, empty, timeout, observer interruption)");
  }
}