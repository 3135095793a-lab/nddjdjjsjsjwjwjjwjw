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
    System.out.println("2 worker lifecycle tests passed");
  }
}