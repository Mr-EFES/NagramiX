import Foundation
@main struct HybridPlacementTests {
 static func main() {
  var count=0
  func check(_ value:Bool) {precondition(value);count += 1}
  for height in [320.0,390,568,667,844,932,1024] {
   for y in stride(from:0.0,through:height,by:7) {
    for delta in [-500.0,-60,-1,1,60,500] {
     check(NagramiXHybridPiPPlacement.half(deltaY:delta,releaseY:y,midpointY:height/2,swipe:true) == (delta < 0 ? 0:1))
     check(NagramiXHybridPiPPlacement.half(deltaY:delta,releaseY:y,midpointY:height/2,swipe:false) == (y < height/2 ? 0:1))
    }
   }
  }
  for invalid in [Double.nan,.infinity,-.infinity] {
   check(NagramiXHybridPiPPlacement.half(deltaY:invalid,releaseY:1,midpointY:2,swipe:true)==nil)
   check(NagramiXHybridPiPPlacement.half(deltaY:1,releaseY:invalid,midpointY:2,swipe:true)==nil)
  }
  print("PASS \(count) production direction/half checks; UIKit/AVKit not executed")
 }
}
